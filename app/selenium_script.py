import os
import time
import logging
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

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Define logger
logger = logging.getLogger(__name__)

def remove_numbering_and_format(text):
    """
    Removes any numbering format like '1) ' or '2) ' from the text and replaces it with '- '.
    """
    lines = text.split('\n')
    formatted_lines = [re.sub(r'^\d+\)\s*', '- ', line.strip()) for line in lines]
    return '\n'.join(formatted_lines)

def split_pros_cons(text):
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
    driver = None
    
    try:
        if run_env == 'ec2':
            logger.info("Running in EC2 environment")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            service = Service(executable_path="/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("ChromeDriver initialized successfully")
        else:
            logger.info("Running in local environment")
            chrome_options = Options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome service & driver instantiated")

        # Rest of your selenium script...
        # ... existing code ...

        current_url = driver.current_url
        modified_url = clean_url(current_url)
        logger.info(f"Successfully created Kialo discussion: {modified_url}")
        driver.quit()
        return modified_url

    except (TimeoutException, WebDriverException) as e:
        logger.error(f"Selenium script execution failed: {str(e)}")
        if driver:
            driver.quit()
        return None
    except Exception as e:
        logger.error(f"Unexpected error in selenium script: {str(e)}")
        if driver:
            driver.quit()
        return None