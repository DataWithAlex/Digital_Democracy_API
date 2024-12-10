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
from .logger_config import logger

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

def run_selenium_script(title, summary, pros_text, cons_text):
    """Run the Selenium script with enhanced logging"""
    try:
        logger.info("Starting Selenium script")
        
        # Initialize Chrome options
        logger.info("Configuring Chrome options")
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

        # Initialize Chrome service and driver
        logger.info("Initializing Chrome driver")
        service = Service(executable_path="/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("ChromeDriver initialized successfully")

        try:
            # Format pros and cons
            pros_text = remove_numbering_and_format(pros_text)
            cons_text = remove_numbering_and_format(cons_text)
            
            # Split into individual points
            pros = split_pros_cons(pros_text)
            cons = split_pros_cons(cons_text)
            
            # Ensure we have exactly 3 pros and cons
            if len(pros) < 3:
                pros.extend([''] * (3 - len(pros)))
            if len(cons) < 3:
                cons.extend([''] * (3 - len(cons)))
            
            pros_1, pros_2, pros_3 = pros[:3]
            cons_1, cons_2, cons_3 = cons[:3]

            # Truncate summary if needed
            bill_summary_text = summary
            if len(bill_summary_text) > 500:
                last_period_index = bill_summary_text.rfind('.', 0, 500)
                if last_period_index != -1:
                    bill_summary_text = bill_summary_text[:last_period_index + 1]
                else:
                    bill_summary_text = bill_summary_text[:500]

            # Login to Kialo
            logger.info("Logging in to Kialo")
            driver.get("https://www.kialo.com/my")
            
            username = os.environ.get('KIALO_USERNAME')
            password = os.environ.get('KIALO_PASSWORD')
            wait = WebDriverWait(driver, 20)

            username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()
            logger.info("Logged in successfully")

            # Create new discussion
            new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
            new_discussion_button.click()
            logger.info("Creating new discussion")

            # Set discussion settings
            element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
            element.click()
            logger.info("Selected discussion settings")

            # Navigate through setup
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
            next_button.click()

            # Set title and thesis
            name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
            name_field.send_keys(title)

            thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
            thesis_field.send_keys("Test Thesis")
            logger.info("Added title and thesis")

            # Continue setup
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
            next_button.click()

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
            next_button.click()

            # Upload image
            script_directory = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_directory, 'image.png')
            logger.info(f"Uploading image from {image_path}")

            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][data-testid='image-upload-input-element']")
            driver.execute_script("""
                arguments[0].style.height='1px';
                arguments[0].style.width='1px';
                arguments[0].style.opacity=1;
                arguments[0].removeAttribute('hidden');
            """, file_input)

            file_input.send_keys(image_path)
            logger.info("Image uploaded")

            # Add tags and create discussion
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
            logger.info("Adding discussion content")

            # Add bill summary
            bill_summary_ = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S") or contains(text(), "H") or contains(text(), "Thesis")]')))
            bill_summary_.clear()
            bill_summary_.send_keys(bill_summary_text)

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
            next_button.click()

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')))
            next_button.click()

            # Add pros
            for pro_text in [pros_1, pros_2, pros_3]:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
                next_button.click()

                pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
                pro.clear()
                pro.send_keys(pro_text)

                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
                next_button.click()

            # Add cons
            for con_text in [cons_1, cons_2, cons_3]:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
                next_button.click()

                con = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
                con.clear()
                con.send_keys(con_text)

                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
                next_button.click()

            # Publish discussion
            share_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@class,'share-discussion-button')]")))
            kialo_discussion_url = share_link.get_attribute('href')
            logger.info(f"Discussion created at: {kialo_discussion_url}")

            driver.get(kialo_discussion_url)

            share_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Publish Discussion']")))
            share_button.click()

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
            next_button.click()

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
            next_button.click()

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Publish")]')))
            next_button.click()

            # Get final URL
            current_url = driver.current_url
            modified_url = clean_url(current_url)
            logger.info(f"Final Kialo URL: {modified_url}")
            
            return modified_url

        except Exception as e:
            logger.error(f"Selenium operation failed: {str(e)}", exc_info=True)
            raise
        finally:
            logger.info("Closing Chrome driver")
            driver.quit()

    except Exception as e:
        logger.error(f"Selenium script failed: {str(e)}", exc_info=True)
        raise