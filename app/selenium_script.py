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

def run_selenium_script(title, summary, pros_text, cons_text):
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

        os.environ['KIALO_USERNAME'] = 'explore@datawithalex.com'
        os.environ['KIALO_PASSWORD'] = '%Mineguy29'

        # Format and process pros and cons
        pros_text = remove_numbering_and_format(pros_text)
        cons_text = remove_numbering_and_format(cons_text)
        
        cons = split_pros_cons(cons_text)
        pros = split_pros_cons(pros_text)
        
        # Ensure we have enough pros and cons
        if len(cons) < 3:
            logger.warning(f"Not enough cons provided: {cons}")
            cons += [''] * (3 - len(cons))
        if len(pros) < 3:
            logger.warning(f"Not enough pros provided: {pros}")
            pros += [''] * (3 - len(pros))

        cons_1, cons_2, cons_3 = cons[0], cons[1], cons[2]
        pros_1, pros_2, pros_3 = pros[0], pros[1], pros[2]

        # Truncate summary if needed
        bill_summary_text = summary
        if len(bill_summary_text) > 500:
            last_period_index = bill_summary_text.rfind('.', 0, 500)
            if last_period_index != -1:
                bill_summary_text = bill_summary_text[:last_period_index + 1]
            else:
                bill_summary_text = bill_summary_text[:500]

        # Start Kialo automation
        driver.get("https://www.kialo.com/my")
        wait = WebDriverWait(driver, 20)

        # Login
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

        username_field.send_keys(os.environ.get('KIALO_USERNAME'))
        password_field.send_keys(os.environ.get('KIALO_PASSWORD'))
        login_button.click()
        logger.info("Logged in to Kialo")

        # Create new discussion
        new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
        new_discussion_button.click()

        # Rest of the Kialo automation...
        # ... (keeping the existing automation steps)

        current_url = driver.current_url
        modified_url = clean_url(current_url)
        logger.info(f"Successfully created Kialo discussion: {modified_url}")
        
        if driver:
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