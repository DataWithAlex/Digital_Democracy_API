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
from .utils import categories, get_category_ids, category_dict  # Added category_dict here
from .logger_config import logger

# Ensure that the OpenAI API key is set
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_top_categories(bill_text, categories, model="gpt-4"):
    # Prepare the system message with instructions
    system_message = (
        "You are an AI that categorizes legislative texts into predefined categories. "
        "You will receive a list of categories and the text of a legislative bill. "
        "Your task is to select the three most relevant categories for the given text."
    )
    
    # Construct the list of categories as a user message
    categories_list = "\n".join([f"- {category['name']}: {category['id']}" for category in categories])
    user_message = f"Here is a list of categories:\n{categories_list}\n\nBased on the following bill text, select the three most relevant categories:\n{bill_text}\nNOTE: YOU MUST RETURN THEM IN THE FOLLOWING FORMAT: [Category Name: Category ID]. For example, [Disney: 655288ef928edb128306742c]"

    # Create the ChatCompletion request using the GPT-4 model
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
        )
        
        # Extract the response content
        top_categories_response = response['choices'][0]['message']['content']
        
        # Log the response for debugging purposes
        logger.info(f"OpenAI Category Response: {top_categories_response}")
        
        # Split the response into individual categories
        top_categories = [category.strip() for category in top_categories_response.split("\n") if category.strip()]
        return top_categories
    
    # Handle any exceptions and log the error message
    except Exception as e:
        logger.error(f"Error in OpenAI category generation: {str(e)}")
        return []

def format_categories_for_webflow(openai_output):
    """
    Formats the OpenAI output for Webflow by extracting valid category IDs.

    Parameters:
    - openai_output (list): A list of category names and IDs returned by OpenAI.

    Returns:
    - list: A list of valid category IDs that match the categories in the OpenAI output.
    """
    # Initialize an empty list to store valid category IDs
    category_ids = []

    # Debug log the OpenAI output
    logger.info(f"OpenAI Output Before Formatting: {openai_output}")

    # Iterate through each line of the OpenAI output
    for category in openai_output:
        # Extract text within square brackets (e.g., [Category Name: Category ID])
        match = re.search(r'\[(.+?):\s*(.+?)\]', category)
        if match:
            # Extract category name and ID
            category_name, category_id = match.groups()

            # Verify if the category ID exists in the predefined categories
            if category_id in category_dict.values():
                category_ids.append(category_id)
                logger.info(f"Matched category '{category_name}' to ID '{category_id}'")
            else:
                logger.warning(f"Warning: Category ID '{category_id}' not found in predefined categories.")
        else:
            logger.warning(f"Warning: OpenAI output '{category}' does not match the expected format.")

    # If category_ids is empty, log the issue for further debugging
    if not category_ids:
        logger.error(f"Failed to format OpenAI output correctly: {openai_output}")

    return category_ids

def upload_to_s3(bucket_name, file_path):
    try:
        s3_client = boto3.client('s3')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_key = f"bill_details/{timestamp}_{os.path.basename(file_path)}"
        s3_client.upload_file(file_path, bucket_name, file_key, ExtraArgs={'ACL': 'public-read'})
        object_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
        logger.info(f"Uploaded {file_path} to {object_url}")
        return object_url
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise

def download_pdf(pdf_url, local_path="bill_text.pdf"):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            with open(local_path, 'wb') as file:
                file.write(response.content)
            logger.info(f"Downloaded PDF from {pdf_url} to {local_path}")
            return local_path
        else:
            raise Exception(f"Failed to download PDF from {pdf_url}")
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        raise

def fetch_bill_details(bill_page_url):
    base_url = 'https://www.flsenate.gov'
    bill_details = {"title": "", "description": "", "pdf_path": "", "govId": "", "billTextPath": "", "full_text": ""}
    
    # Step 1: Fetch the bill page
    logger.info(f"Fetching bill details from: {urljoin(base_url, bill_page_url)}")
    try:
        response = requests.get(urljoin(base_url, bill_page_url))
        response.raise_for_status()  # Raise an HTTPError if the response code was unsuccessful
        logger.info(f"Successfully fetched bill page content. Status code: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error fetching bill page: {e}")
        raise Exception(f"Failed to fetch bill page due to: {e}")
    
    # Step 2: Parse the bill page content
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        bill_title_tag = soup.find('div', id='prevNextBillNav').find_next('h2')
        
        if bill_title_tag:
            bill_details["title"] = bill_title_tag.get_text(strip=True)
            logger.info(f"Extracted bill title: {bill_details['title']}")
            
            # Extract the Gov ID from the title
            gov_id_match = re.search(r"([A-Z]{2} \d+):", bill_details["title"])
            if gov_id_match:
                bill_details["govId"] = gov_id_match.group(1)
                logger.info(f"Extracted Gov ID: {bill_details['govId']}")
            else:
                logger.warning("Gov ID not found in the bill title.")
        else:
            logger.warning("Bill title not found on the page.")
        
        # Step 3: Find the PDF link for the bill text
        bill_pdf_link = soup.find('a', class_='lnk_BillTextPDF')
        if bill_pdf_link:
            pdf_url = urljoin(base_url, bill_pdf_link['href'])
            logger.info(f"Found bill PDF link: {pdf_url}")
            
            # Step 4: Download the PDF file
            try:
                local_pdf_path = download_pdf(pdf_url)
                bill_details["pdf_path"] = local_pdf_path
                logger.info(f"Downloaded bill PDF to: {local_pdf_path}")
                
                # Step 5: Upload PDF to S3
                try:
                    s3_path = upload_to_s3('ddp-bills-2', local_pdf_path)
                    bill_details["billTextPath"] = s3_path
                    logger.info(f"Uploaded PDF to S3 at: {s3_path}")
                except Exception as e:
                    logger.error(f"Failed to upload PDF to S3: {e}")
                    raise
            except Exception as e:
                logger.error(f"Failed to download PDF from: {pdf_url}, Error: {e}")
                raise
        else:
            logger.warning("PDF link not found on the page.")
        
        # Step 6: Extract text from the PDF
        if bill_details["pdf_path"]:
            try:
                full_text = extract_text_from_pdf(bill_details["pdf_path"])
                bill_details["full_text"] = full_text
                logger.info(f"Extracted full text from PDF. First 500 characters: {full_text[:500]}...")
            except Exception as e:
                logger.error(f"Failed to extract text from PDF at {bill_details['pdf_path']}: {e}")
                raise
        else:
            logger.warning("No PDF path available to extract text.")
        
        # Step 7: Generate categories based on the extracted text
        if bill_details["full_text"]:
            try:
                openai_categories = get_top_categories(bill_details["full_text"], categories)
                formatted_categories = format_categories_for_webflow(openai_categories)
                bill_details["categories"] = formatted_categories
                logger.info(f"Formatted Categories for Webflow: {formatted_categories}")
            except Exception as e:
                logger.error(f"Failed to generate categories using OpenAI: {e}")
                raise
        else:
            logger.warning("No full text available to generate categories.")
        
        return bill_details

    except Exception as e:
        logger.error(f"An error occurred while processing bill details: {e}")
        raise Exception(f"Failed to process bill details due to: {e}")

def extract_text_from_pdf(pdf_path):
    full_text = ""
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            full_text += page.get_text()
    return full_text

def fetch_federal_bill_details(session, bill, bill_type):
    base_url = 'https://www.congress.gov'
    url_mappings = {
        "HR": [
            f'{base_url}/{session}/bills/hr{bill}/BILLS-{session}hr{bill}ih.xml',
            f'{base_url}/{session}/bills/hr{bill}/BILLS-{session}hr{bill}rh.xml'
        ],
        "S": [
            f'{base_url}/{session}/bills/s{bill}/BILLS-{session}s{bill}fps.xml',
            f'{base_url}/{session}/bills/s{bill}/BILLS-{session}s{bill}rs.xml',
            f'{base_url}/{session}/bills/s{bill}/BILLS-{session}s{bill}is.xml'
        ],
        # Add other bill types as needed
    }

    urls = url_mappings.get(bill_type)
    if not urls:
        raise ValueError(f"Unsupported bill type: {bill_type}")

    valid_url = None
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            valid_url = url
            break
        except requests.exceptions.HTTPError:
            continue
    else:
        raise ValueError(f"Bill {bill_type}{bill} not found for session {session}")

    if not response.content:
        raise ValueError("Empty response from Congress.gov")

    soup = BeautifulSoup(response.content, 'lxml-xml')
    bill_text = soup.get_text()
    title_tag = soup.find('title')
    title = title_tag.get_text() if title_tag else f"{bill_type} {bill}"
    description = "No description available"

    local_file_path = save_text_to_file(bill_text)
    bill_text_path = upload_to_s3('ddp-bills-2', local_file_path)

    bill_details = {
        "title": title,
        "description": description,
        "full_text": bill_text,
        "govId": f"{bill_type} {bill}",
        "billTextPath": bill_text_path,
        "history": f"{session}{bill_type}{bill}",
        "gov-url": valid_url,
        "categories": []
    }

    # Generate and format categories using OpenAI
    openai_categories = get_top_categories(bill_text, categories)
    formatted_categories = format_categories_for_webflow(openai_categories)
    bill_details["categories"] = formatted_categories

    return bill_details

def save_text_to_file(text, file_name='temp_path_for_federal_bill.txt'):
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(text)
    return file_name

# Rest of the functions remain the same...


# Function to summarize text with OpenAI
def summarize_with_openai_chat(text, model="gpt-4o"):
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
def full_summarize_with_openai_chat(full_text, model="gpt-4o"):
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
def full_summarize_with_openai_chat_spanish(full_text, model="gpt-4o"):
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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to generate pros for supporting a bill based on its summary. You must specifically have 3 Pros, separated by numbers--no exceptions. Numbers separated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the pros of supporting this bill? make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    cons_response = openai.ChatCompletion.create(
        model="gpt-4o",
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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un asistente útil diseñado para generar ventajas para respaldar una factura en función de su resumen. Debes tener específicamente 3 profesionales, separados por números, sin excepciones. Números separados como 1) 2) 3)"},
            {"role": "user", "content": f"¿Cuáles son las ventajas de apoyar este proyecto de ley? que no sean más de 2 oraciones \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    cons_response = openai.ChatCompletion.create(
        model="gpt-4o",
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

    data_es = [['Contras', 'Pros'], [Paragraph(cons_es, styles['Normal']), Paragraph(pros_es, styles['Normal'])]]
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

def validate_and_generate_pros_cons(full_text):
    pros, cons = generate_pros_and_cons(full_text)
    
    def is_valid_format(text):
        return bool(re.match(r'^\d\).*', text))
    
    if not all(is_valid_format(p) for p in pros.split('\n')) or not all(is_valid_format(c) for c in cons.split('\n')):
        pros, cons = generate_pros_and_cons(full_text)  # Regenerate if invalid format

    return pros, cons