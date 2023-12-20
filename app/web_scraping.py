import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
    :return: A dictionary containing the bill title, description, and local PDF path.
    """
    base_url = 'https://www.flsenate.gov'
    response = requests.get(urljoin(base_url, bill_page_url))

    bill_details = {
        "title": "",
        "description": "",
        "pdf_path": "",  # Changed from pdf_url to pdf_path
    }

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the bill title
        bill_title_tag = soup.find('div', id='prevNextBillNav').find_next('h2')
        if bill_title_tag:
            bill_details["title"] = bill_title_tag.get_text(strip=True)

        # Extract the bill description
        bill_description_tag = soup.find('p', class_='width80')
        if bill_description_tag:
            bill_details["description"] = bill_description_tag.get_text(strip=True)

        # Extract the bill PDF link and download it
        bill_pdf_link = soup.find('a', class_='lnk_BillTextPDF')
        if bill_pdf_link:
            pdf_url = urljoin(base_url, bill_pdf_link['href'])
            bill_details["pdf_path"] = download_pdf(pdf_url)

    return bill_details
