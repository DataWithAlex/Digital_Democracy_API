import os
import re
from urllib.parse import urljoin
from datetime import datetime
import logging
import boto3
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .translation import translate_to_spanish
import openai

# Ensure that the OpenAI API key is set
from .dependencies import openai_api_key
openai.api_key = openai_api_key

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to upload files to S3
def upload_to_s3(bucket_name, file_path):
    try:
        s3_client = boto3.client('s3')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_key = f"bill_details/{timestamp}_{file_path.split('/')[-1]}"
        s3_client.upload_file(file_path, bucket_name, file_key, ExtraArgs={'ACL': 'public-read'})
        object_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
        logging.info(f"Uploaded {file_path} to {object_url}")
        return object_url
    except Exception as e:
        logging.error(f"Failed to upload to S3: {e}")
        raise

# Function to download PDFs
def download_pdf(pdf_url, local_path="bill_text.pdf"):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            with open(local_path, 'wb') as file:
                file.write(response.content)
            logging.info(f"Downloaded PDF from {pdf_url} to {local_path}")
            return local_path
        else:
            raise Exception(f"Failed to download PDF from {pdf_url}")
    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        raise

# Function to fetch bill details
def fetch_bill_details(bill_page_url):
    base_url = 'https://www.flsenate.gov'
    response = requests.get(urljoin(base_url, bill_page_url))
    bill_details = {"title": "", "description": "", "pdf_path": "", "govId": "", "billTextPath": ""}

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

def fetch_federal_bill_details(session, bill, bill_type):
def fetch_federal_bill_details(session, bill, bill_type):
    base_url = 'https://www.congress.gov'
    url_mappings = {
        "HR": f'{base_url}/{session}/bills/hr{bill}/BILLS-{session}hr{bill}rh.xml',
        "S": f'{base_url}/{session}/bills/s{bill}/BILLS-{session}s{bill}fps.xml',
        "H.Res": f'{base_url}/{session}/bills/hres{bill}/BILLS-{session}hres{bill}rh.xml',
        "S.Res": f'{base_url}/{session}/bills/sres{bill}/BILLS-{session}sres{bill}lts.xml',
        "H.J.Res": f'{base_url}/{session}/bills/hjres{bill}/BILLS-{session}hjres{bill}ih.xml',
        "S.J.Res": f'{base_url}/{session}/bills/sjres{bill}/BILLS-{session}sjres{bill}rs.xml',
        "H.Con.Res": f'{base_url}/{session}/bills/hconres{bill}/BILLS-{session}hconres{bill}ih.xml',
        "S.Con.Res": f'{base_url}/{session}/bills/sconres{bill}/BILLS-{session}sconres{bill}ats.xml'
    }

    url = url_mappings.get(bill_type)
    if not url:
        raise ValueError(f"Unsupported bill type: {bill_type}")

    response = requests.get(url)
    response.raise_for_status()

    # Check if response content is empty
    if not response.content:
        raise ValueError("Empty response from Congress.gov")

    # Use lxml-xml parser
    soup = BeautifulSoup(response.content, 'lxml-xml')
    bill_text = soup.get_text()

    # Extracting title for the sake of the example
    title = soup.find('title').get_text() if soup.find('title') else "No title available"
    description = "No description available"

    # Create a local file with the extracted bill text
    local_file_path = 'temp_path_for_federal_bill.txt'
    with open(local_file_path, 'w', encoding='utf-8') as file:
        file.write(bill_text)

    # Upload the local file to S3
    bill_text_path = upload_to_s3('ddp-bills-2', local_file_path)

    # Construct bill details dictionary
    bill_details = {
        "title": title,
        "description": description,
        "full_text": bill_text,
        "govId": f"{session}_{bill}",
        "billTextPath": bill_text_path
    }
    return bill_details

# Function to summarize text with OpenAI
def summarize_with_openai_chat(text, model="gpt-4-turbo-preview"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are going to generate a 1-3 sentence response summarizing each page of a bill passed in the Florida senate. You will receive the raw text of each page."},
            {"role": "user", "content": text}
        ]
    )
    content = response['choices'][0]['message']['content']
    return content

# Function to summarize full text with OpenAI
def full_summarize_with_openai_chat(full_text, model="gpt-4-turbo-preview"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are going to generate a 3-4 sentence response summarizing each page of a bill passed in the Florida senate. You will receive the raw text of each page. Do not include the title of the bills in the summary or the reference numbers. do not mention bill number either. dont include HB "},
            {"role": "user", "content": f"Please summarize the following text:\n\n{full_text}"}
        ]
    )
    summary = response['choices'][0]['message']['content']
    return summary

# Function to summarize full text with OpenAI in Spanish
def full_summarize_with_openai_chat_spanish(full_text, model="gpt-4-turbo-preview"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "Vas a generar una respuesta de 3 a 4 oraciones que resuma cada página de un proyecto de ley aprobado en el Senado de Florida. Recibirá el texto sin formato de cada página. No incluir el título de los proyectos de ley en el resumen ni los números de referencia. Tampoco menciones el número de factura. "},
            {"role": "user", "content": f"Por favor resuma el siguiente texto:\n\n{full_text}"}
        ]
    )
    summary = response['choices'][0]['message']['content']
    return summary

# Function to generate pros and cons
def generate_pros_and_cons(full_text):
    pros_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to generate pros for supporting a bill based on its summary. You must specifically have 3 Pros, separated by numbers--no exceptions. Numbers separated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the pros of supporting this bill? make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    cons_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to generate cons against supporting a bill based on its summary. You must have specifically 3 Cons, separated by numbers--no exceptions. Numbers separated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the cons of supporting this bill? Make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    cons = cons_response['choices'][0]['message']['content']

    return pros, cons

# Function to generate pros and cons in Spanish
def generate_pros_and_cons_spanish(full_text):
    pros_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "Eres un asistente útil diseñado para generar ventajas para respaldar una factura en función de su resumen. Debes tener específicamente 3 profesionales, separados por números, sin excepciones. Números separados como 1) 2) 3)"},
            {"role": "user", "content": f"¿Cuáles son las ventajas de apoyar este proyecto de ley? que no sean más de 2 oraciones \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    cons_response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "Usted es un asistente útil diseñado para generar desventajas contra el respaldo de un proyecto de ley en función de su resumen. Debes tener específicamente 3 desventajas, separadas por números, sin excepciones. Números separados como 1) 2) 3)"},
            {"role": "user", "content": f"¿Cuáles son las desventajas de apoyar este proyecto de ley? Que no tenga más de 2 oraciones. \n\n{full_text}"}
        ]
    )
    cons = cons_response['choices'][0]['message']['content']

    return pros, cons

# Function to create summary PDF
def create_summary_pdf(input_pdf_path, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    full_text = ""
    with fitz.open(input_pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            full_text += text + " "

    summary = full_summarize_with_openai_chat(full_text)
    pros, cons = generate_pros_and_cons(full_text)

    story.append(Paragraph(f"<b>Summary:</b><br/>{summary}", styles['Normal']))
    story.append(Spacer(1, 12))

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

    doc.build(story)

    return os.path.abspath(output_pdf_path), summary, pros, cons

# Function to create summary PDF in Spanish
def create_summary_pdf_spanish(input_pdf_path, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    full_text = ""
    with fitz.open(input_pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            full_text += text + " "

    if not full_text.strip():
        logging.error("No text extracted from PDF for translation.")
        return None

    summary = full_summarize_with_openai_chat(full_text)
    summary_es = translate_to_spanish(summary)
    pros, cons = generate_pros_and_cons(full_text)
    pros_es = translate_to_spanish(pros)
    cons_es = translate_to_spanish(cons)

    story.append(Paragraph(f"<b>Summary:</b><br/>{summary_es}", styles['Normal']))
    story.append(Spacer(1, 12))

    col_widths = [width * 0.45, width * 0.45]

    data_es = [['Cons', 'Pros'], [Paragraph(cons_es, styles['Normal']), Paragraph(pros_es, styles['Normal'])]]
    t_es = Table(data_es, colWidths=col_widths)
    t_es.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    story.append(t_es)

    doc.build(story)

    return os.path.abspath(output_pdf_path), summary_es, pros_es, cons_es

# Function to create federal summary PDF
def create_federal_summary_pdf(full_text, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    summary = full_summarize_with_openai_chat(full_text)
    pros, cons = generate_pros_and_cons(full_text)

    story.append(Paragraph(f"<b>Summary:</b><br/>{summary}", styles['Normal']))
    story.append(Spacer(1, 12))

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

    doc.build(story)

    return os.path.abspath(output_pdf_path), summary, pros, cons

# Function to create federal summary PDF in Spanish
def create_federal_summary_pdf_spanish(full_text, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    summary = full_summarize_with_openai_chat_spanish(full_text)
    pros, cons = generate_pros_and_cons_spanish(full_text)

    story.append(Paragraph(f"<b>Resumen:</b><br/>{summary}", styles['Normal']))
    story.append(Spacer(1, 12))

    data = [['Contras', 'Pros'], [Paragraph(cons, styles['Normal']), Paragraph(pros, styles['Normal'])]]
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

    doc.build(story)

    return os.path.abspath(output_pdf_path), summary, pros, cons
