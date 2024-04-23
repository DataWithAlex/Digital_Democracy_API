import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import boto3
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import boto3
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
