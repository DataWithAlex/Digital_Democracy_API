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
from .logger_config import selenium_logger as logger

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

def run_selenium_script(title, summary, pros_text, cons_text):
    """Run the Selenium script with enhanced logging"""
    try:
        run_env = 'ec2'
        logger.info("Starting Kialo discussion creation process")
        
        # Configure Chrome options based on environment
        if run_env == 'ec2':
            logger.info("Configuring Chrome for EC2 environment")
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
        else:
            chrome_options = Options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver initialized in local environment")

        # Set up WebDriverWait
        wait = WebDriverWait(driver, 10)

        # Navigate to Kialo
        driver.get("https://www.kialo.com/")
        logger.info("Navigating to Kialo website")

        # Get environment variables
        kialo_username = os.environ.get('KIALO_USERNAME')
        kialo_password = os.environ.get('KIALO_PASSWORD')

        if not kialo_username or not kialo_password:
            raise ValueError("Kialo credentials not found in environment variables")

        # Login process
        logger.info("Starting Kialo authentication")
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

        username_field.send_keys(kialo_username)
        password_field.send_keys(kialo_password)
        login_button.click()
        logger.info("Successfully authenticated with Kialo")

        # Create new discussion
        logger.info("Starting discussion creation process")
        new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
        new_discussion_button.click()

        # Set discussion settings
        element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
        element.click()

        # Navigate through setup
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        # Set title and thesis
        name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
        name_field.send_keys(title)

        thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
        thesis_field.send_keys("Test Thesis")
        logger.info("Discussion title and thesis configured")

        # Continue setup
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        # Upload image
        script_directory = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_directory, 'image.png')
        logger.info("Uploading discussion image")

        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][data-testid='image-upload-input-element']")
        driver.execute_script("""
            arguments[0].style.height='1px';
            arguments[0].style.width='1px';
            arguments[0].style.opacity=1;
            arguments[0].removeAttribute('hidden');
        """, file_input)

        file_input.send_keys(image_path)
        logger.info("Discussion image uploaded successfully")

        # Add tags and create discussion
        logger.info("Configuring discussion tags")
        tags_input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.pill-editor-input")))
        tags_input_field.clear()
        tags_input_field.send_keys("DDP")
        tags_input_field.send_keys(Keys.ENTER)

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Create")]')))
        next_button.click()

        # Add content
        time.sleep(10)
        current_url = driver.current_url
        x = current_url[-5:]
        new_url = f"{current_url}?path={x}.0~{x}.3&active=~{x}.3&action=edit"
        driver.get(new_url)
        logger.info("Adding discussion content and arguments")

        # Add bill summary
        bill_summary_ = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S") or contains(text(), "H") or contains(text(), "Thesis")]')))
        bill_summary_.clear()
        bill_summary_.send_keys(bill_summary_text)

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')))
        next_button.click()

        # Add pros
        logger.info("Adding pro arguments to discussion")
        for pro_text in [pros_1, pros_2, pros_3]:
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
            next_button.click()

            pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
            pro.clear()
            pro.send_keys(pro_text)

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
            next_button.click()

        # Add cons
        logger.info("Adding con arguments to discussion")
        for con_text in [cons_1, cons_2, cons_3]:
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
            next_button.click()

            con = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
            con.clear()
            con.send_keys(con_text)

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
            next_button.click()

        logger.info("Discussion creation completed successfully")
        return current_url

    except Exception as e:
        logger.error(f"Error during Kialo discussion creation: {str(e)}")
        raise e

    finally:
        if 'driver' in locals():
            driver.quit()
            logger.info("Chrome driver closed")