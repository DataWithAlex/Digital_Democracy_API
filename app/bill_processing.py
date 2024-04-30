import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import boto3
from datetime import datetime
import logging
import openai
import os
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key

# Constants
BUCKET_NAME = "ddp-bills-2"

def upload_to_s3(file_path):
    """
    Uploads a file to an S3 bucket.
    """
    s3_client = boto3.client('s3')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_key = f"bill_details/{timestamp}_{file_path.split('/')[-1]}"
    s3_client.upload_file(file_path, BUCKET_NAME, file_key, ExtraArgs={'ACL': 'public-read'})
    object_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
    logging.info(f"Uploaded {file_path} to {object_url}")
    return object_url

def download_pdf(pdf_url, local_path="bill_text.pdf"):
    """
    Downloads a PDF from a given URL.
    """
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(local_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded PDF from {pdf_url} to {local_path}")
        return local_path
    else:
        raise Exception(f"Failed to download PDF from {pdf_url}")

def fetch_bill_details(bill_page_url):
    """
    Fetches details of a bill from the Florida Senate Bill page.
    """
    try:
        base_url = 'https://www.flsenate.gov'
        response = requests.get(urljoin(base_url, bill_page_url))
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            bill_title_tag = soup.find('div', id='prevNextBillNav').find_next('h2')
            bill_pdf_link = soup.find('a', class_='lnk_BillTextPDF')
            
            title = bill_title_tag.get_text(strip=True) if bill_title_tag else ''
            gov_id = re.search(r"([A-Z]{2} \d+):", title).group(1) if title else ''
            pdf_url = urljoin(base_url, bill_pdf_link['href']) if bill_pdf_link else ''
            local_pdf_path = download_pdf(pdf_url)
            s3_pdf_path = upload_to_s3(local_pdf_path)

            return {
                "title": title,
                "govId": gov_id,
                "pdf_path": s3_pdf_path
            }
        else:
            raise Exception("Failed to fetch bill details due to HTTP error.")
    except Exception as e:
        logging.error(f"Error fetching bill details: {e}")
        raise

def generate_pros_and_cons(full_text, language='EN'):
    """
    Generates pros and cons of a bill using OpenAI's API.
    """
    pros_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": f"You are a helpful assistant designed to generate pros for supporting a bill based on its summary. You must specifically have 3 Pros, separated by numbers--no exceptions. Numbers separated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the pros of supporting this bill? Make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    cons_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": f"You are a helpful assistant designed to generate cons against supporting a bill based on its summary. You must specifically have 3 Cons, separated by numbers--no exceptions. Numbers separated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the cons of supporting this bill? Make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']
    cons = cons_response['choices'][0]['message']['content']

    return pros, cons

def create_summary_pdf(bill_page_url, output_pdf_path):
    """
    Creates a PDF summary of a bill.
    """
    try:
        bill_details = fetch_bill_details(bill_page_url)
        title = bill_details["title"]
        pdf_url = bill_details["pdf_path"]
        full_text_path = download_pdf(pdf_url)
        
        width, height = letter
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        story = []

        # Add title
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 12))

        # Extract text from PDF
        with fitz.open(full_text_path) as pdf:
            full_text = ""
            for page in pdf:
                full_text += page.get_text()

        summary, pros, cons = generate_pros_and_cons(full_text)

        # Add content to the document
        story.append(Paragraph(f"<b>Summary:</b><br/>{summary}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Creating a table for pros and cons
        data = [['Cons', 'Pros'], [Paragraph(cons, styles['Normal']), Paragraph(pros, styles['Normal'])]]
        col_widths = [width * 0.45, width * 0.45]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        story.append(t)

        # Build the PDF
        doc.build(story)
        logging.info(f"Summary PDF created at {output_pdf_path}")

    except Exception as e:
        logging.error(f"Error creating summary PDF: {e}")
        raise

# Example usage
bill_page_url = "/Session/Bill/2022/1468"
create_summary_pdf(bill_page_url, "bill_summary.pdf")
