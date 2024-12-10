import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from .logger_config import selenium_logger

def remove_numbering_and_format(text):
    """
    Removes any numbering format like '1) ' or '2) ' from the text and replaces it with '- '.
    """
    lines = text.split('\n')
    formatted_lines = [re.sub(r'^\d+\)\s*', '- ', line.strip()) for line in lines]
    return '\n'.join(formatted_lines)

def split_pros_cons(text):
    # Splitting lines using common delimiters including numbers or bullet points
    pattern = r'(^-|\d+\))\s*'
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    sections = []
    
    for i, match in enumerate(matches):
        start = match.start()
        if i < len(matches) - 1:
            end = matches[i + 1].start()
            sections.append(text[start:end].strip())
        else:
            sections.append(text[start:].strip())
    
    return sections

def clean_url(url):
    cleaned_url = url.split("/permissions")[0] + "/"
    return cleaned_url

async def run_selenium_script(title, summary, pros_text, cons_text):
    run_env = 'ec2'
    
    if run_env == 'ec2':
        selenium_logger.info("Running in EC2 environment")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--v=1")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--start-maximized")

        service = Service(executable_path="/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        selenium_logger.info("ChromeDriver initialized successfully")
        
    else:
        selenium_logger.info("Running in local environment")
        chrome_options = Options()
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        selenium_logger.info("Chrome service & driver instantiated")

    try:
        # Formatting pros and cons to remove numbers and replace with bullet points
        pros_text = remove_numbering_and_format(pros_text)
        cons_text = remove_numbering_and_format(cons_text)
        
        # Split the formatted text into individual pros and cons
        cons = split_pros_cons(cons_text)
        pros = split_pros_cons(pros_text)
        
        selenium_logger.debug(f"Formatted pros: {pros}")
        selenium_logger.debug(f"Formatted cons: {cons}")

        # Check and ensure the cons and pros have content
        if len(cons) < 3:
            selenium_logger.warning(f"Not enough cons provided: {cons}")
            cons += [''] * (3 - len(cons))

        if len(pros) < 3:
            selenium_logger.warning(f"Not enough pros provided: {pros}")
            pros += [''] * (3 - len(pros))

        cons_1, cons_2, cons_3 = cons[0], cons[1], cons[2]
        pros_1, pros_2, pros_3 = pros[0], pros[1], pros[2]

        bill_summary_text = summary
        if len(bill_summary_text) > 500:
            last_period_index = bill_summary_text.rfind('.', 0, 500)
            if last_period_index != -1:
                bill_summary_text = bill_summary_text[:last_period_index + 1]
            else:
                bill_summary_text = bill_summary_text[:500]

        driver.get("https://www.kialo.com/my")
        selenium_logger.info("Navigating to Kialo login page")

        username = os.environ.get('KIALO_USERNAME')
        password = os.environ.get('KIALO_PASSWORD')

        wait = WebDriverWait(driver, 20)

        # Rest of the selenium script with updated logging...
        # ... existing code ...

        current_url = driver.current_url
        modified_url = clean_url(current_url)
        selenium_logger.info(f"Successfully created Kialo discussion: {modified_url}")
        driver.quit()

        return modified_url

    except (TimeoutException, WebDriverException) as e:
        selenium_logger.error(f"Selenium script execution failed: {str(e)}", exc_info=True)
        if driver:
            driver.quit()
        raise
    except Exception as e:
        selenium_logger.error(f"Unexpected error in selenium script: {str(e)}", exc_info=True)
        if driver:
            driver.quit()
        raise