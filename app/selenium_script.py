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
import asyncio
from .logger_config import selenium_logger

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Define logger
logger = logging.getLogger(__name__)

# Set selenium logger to only show warnings and above
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.WARNING)

# Set urllib3 logger to only show warnings and above
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.WARNING)

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
    """
    Run the selenium script to create a Kialo discussion.
    This is a long-running process that may take several minutes to complete.
    Returns the Kialo URL or None if there's an error.
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # Set up logging preferences to reduce noise
    chrome_options.add_argument('--log-level=3')  # FATAL
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        selenium_logger.info(f"Starting Kialo automation for bill: {title}")
        
        # Create driver in a separate thread to not block the event loop
        loop = asyncio.get_event_loop()
        driver = await loop.run_in_executor(None, 
            lambda: webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                   options=chrome_options))

        try:
            # Navigate to Kialo
            await loop.run_in_executor(None, driver.get, "https://www.kialo.com/")
            selenium_logger.info("Navigated to Kialo homepage")

            # Click login button (wait up to 60 seconds for initial load)
            login_button = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="landing-page-header-login-button"]')))
            await loop.run_in_executor(None, login_button.click)
            selenium_logger.info("Clicked login button")

            # Fill in credentials (wait up to 60 seconds for form)
            email_field = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.NAME, "email")))
            await loop.run_in_executor(None, email_field.send_keys, os.getenv('KIALO_EMAIL'))

            password_field = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.NAME, "password")))
            await loop.run_in_executor(None, password_field.send_keys, os.getenv('KIALO_PASSWORD'))

            # Submit login form
            submit_button = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="auth-page-form-submit"]')))
            await loop.run_in_executor(None, submit_button.click)
            selenium_logger.info("Logged in successfully")

            # Wait for the create discussion button and click it (longer wait after login)
            create_discussion = await loop.run_in_executor(None,
                WebDriverWait(driver, 90).until,
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="create-discussion-button"]')))
            await loop.run_in_executor(None, create_discussion.click)
            selenium_logger.info("Clicked create discussion button")

            # Fill in the discussion details
            title_field = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="create-discussion-title"]')))
            await loop.run_in_executor(None, title_field.send_keys, title)

            background_field = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="create-discussion-background"]')))
            await loop.run_in_executor(None, background_field.send_keys, summary)

            thesis_field = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="create-discussion-thesis"]')))
            await loop.run_in_executor(None, thesis_field.send_keys, "Should this bill be passed?")

            # Create discussion
            create_button = await loop.run_in_executor(None,
                WebDriverWait(driver, 60).until,
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="create-discussion-submit"]')))
            await loop.run_in_executor(None, create_button.click)
            selenium_logger.info("Created discussion")

            # Wait for the discussion to be created and get the URL (longer wait for creation)
            await asyncio.sleep(5)  # Give more time for the URL to update
            current_url = await loop.run_in_executor(None, lambda: driver.current_url)
            selenium_logger.info(f"Discussion created at URL: {current_url}")

            return current_url

        except TimeoutException as e:
            selenium_logger.error(f"Timeout while executing Selenium script: {str(e)}")
            return None
        except Exception as e:
            selenium_logger.error(f"Error in Selenium script: {str(e)}")
            return None
        finally:
            await loop.run_in_executor(None, driver.quit)
            selenium_logger.info("Selenium driver closed")

    except Exception as e:
        selenium_logger.error(f"Failed to initialize Selenium: {str(e)}")
        return None