import os
import logging
from datetime import datetime
import boto3
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import openai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Constants
BUCKET_NAME = "ddp-bills-2"


def upload_to_s3(file_path):
    """
    Uploads a file to an S3 bucket.
    """
    s3_client = boto3.client('s3')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_key = f"bill_details/{timestamp}_{os.path.basename(file_path)}"
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
    Fetches details of a bill from the Florida Senate Bill page and downloads its PDF.
    :param bill_page_url: URL of the specific bill page.
    :return: A dictionary containing the bill title, description, local PDF path, govId, and billTextPath.
    """
    try:
        base_url = 'https://www.flsenate.gov'
        response = requests.get(urljoin(base_url, bill_page_url))
        bill_details = {"title": "", "description": "", "pdf_path": "", "govId": "", "billTextPath": ""}

        bill_details = {
            "title": "",
            "description": "",
            "pdf_path": "",
            "govId": "",  # govId extracted from title
            "billTextPath": ""  # URL of the uploaded file on S3
        }

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            bill_title_tag = soup.find('div', id='prevNextBillNav').find_next('h2')
            if bill_title_tag:
                bill_details["title"] = bill_title_tag.get_text(strip=True)
                gov_id_match = re.search(r"([A-Z]{2} \d+):", bill_details["title"])
                if gov_id_match:
                    bill_details["govId"] = gov_id_match.group(1)

            bill_pdf_link = soup.find('a', class_='lnk_BillTextPDF')
            if bill_pdf_link:
                pdf_url = urljoin(base_url, bill_pdf_link['href'])
                local_pdf_path = download_pdf(pdf_url)
                bill_details["pdf_path"] = local_pdf_path
                bill_details["billTextPath"] = upload_to_s3('ddp-bills-2', local_pdf_path)
            return bill_details
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


def create_summary_pdf(bill_details, output_pdf_path):
    """
    Creates a summary PDF with the bill details and pros and cons.
    """
    try:
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add Title
        title = bill_details['title']
        story.append(Paragraph(title, styles['Title']))

        # Add Spacer
        story.append(Spacer(1, 12))

        # Add Bill Details Table
        gov_id = bill_details['govId']
        pdf_path = bill_details['pdf_path']

        details_data = [
            ["Title", title],
            ["Government ID", gov_id],
            ["PDF", pdf_path]
        ]
        details_table = Table(details_data, colWidths=[120, 400], rowHeights=30)
        details_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                                           ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                           ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                           ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                           ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                           ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                           ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        story.append(details_table)

        # Add Spacer
        story.append(Spacer(1, 12))

        # Add Pros and Cons
        summary = bill_details['summary']
        pros = bill_details['pros']
        cons = bill_details['cons']
        pros_para = Paragraph("<b>Pros:</b><br/>" + pros, styles['Normal'])
        cons_para = Paragraph("<b>Cons:</b><br/>" + cons, styles['Normal'])
        story.extend([pros_para, cons_para])

        # Build PDF
        doc.build(story)
        logging.info(f"Summary PDF generated successfully: {output_pdf_path}")
    except Exception as e:
        logging.error(f"Error generating summary PDF: {e}")
        raise



def process_bill_page(bill_page_url):
    """
    Processes a bill page, fetches details, generates pros and cons, and creates summary PDF.
    """
    try:
        summary_pdf_path = create_summary_pdf(bill_page_url)
        return summary_pdf_path
    except Exception as e:
        logging.error(f"Error processing bill page: {e}")
        raise
