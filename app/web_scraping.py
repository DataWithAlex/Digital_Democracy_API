import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import boto3
from datetime import datetime

#def upload_to_s3(bucket_name, file_path):
#    s3_client = boto3.client('s3')
#    # Generate a unique file key using the current timestamp
#    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#    file_key = f"bill_details/{timestamp}_{file_path.split('/')[-1]}"
#    s3_client.upload_file(file_path, bucket_name, file_key, ExtraArgs={'ACL': 'public-read'})
#    object_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
#    return object_url

def upload_to_s3(bucket_name, file_path):
    s3_client = boto3.client('s3')
    # Generate a unique file key using the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_key = f"bill_details/{timestamp}_{file_path.split('/')[-1]}"
    s3_client.upload_file(file_path, bucket_name, file_key)  # Removed ExtraArgs
    object_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
    return object_url

def download_pdf(pdf_url, local_path="bill_text.pdf"):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(local_path, 'wb') as file:
            file.write(response.content)
        return local_path
    else:
        raise Exception(f"Failed to download PDF from {pdf_url}")

def fetch_bill_details(bill_page_url):
    """
    Fetches details of a bill from the Florida Senate Bill page and downloads its PDF.
    :param bill_page_url: URL of the specific bill page.
    :return: A dictionary containing the bill title, description, local PDF path, govId, and billTextPath.
    """
    base_url = 'https://www.flsenate.gov'
    response = requests.get(urljoin(base_url, bill_page_url))

    bill_details = {
        "title": "",
        "description": "",
        "pdf_path": "",
        "govId": "",  # govId extracted from title
        "billTextPath": ""  # URL of the uploaded file on S3
    }

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the bill title and govId
        bill_title_tag = soup.find('div', id='prevNextBillNav').find_next('h2')
        if bill_title_tag:
            bill_details["title"] = bill_title_tag.get_text(strip=True)

            # Extract govId using a regular expression
            gov_id_match = re.search(r"([A-Z]{2} \d+):", bill_details["title"])
            if gov_id_match:
                bill_details["govId"] = gov_id_match.group(1)

        # Extract and download the bill PDF
        bill_pdf_link = soup.find('a', class_='lnk_BillTextPDF')
        if bill_pdf_link:
            pdf_url = urljoin(base_url, bill_pdf_link['href'])
            local_pdf_path = download_pdf(pdf_url)
            bill_details["pdf_path"] = local_pdf_path

            # Upload to S3 and get the URL
            bill_details["billTextPath"] = upload_to_s3('ddp-bills-2', local_pdf_path)  # Adjust as needed

    return bill_details
