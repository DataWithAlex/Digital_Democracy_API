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
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from .logger_config import selenium_logger as logger

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

def wait_and_find_element(driver, by, value, timeout=20, retries=3):
    """Helper function to wait for and find an element with retries"""
    for attempt in range(retries):
        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            wait.until(EC.element_to_be_clickable((by, value)))
            return element
        except (TimeoutException, NoSuchElementException) as e:
            if attempt == retries - 1:
                raise e
            logger.warning(f"Attempt {attempt + 1} failed to find element {value}. Retrying...")
            time.sleep(2)

def run_selenium_script(title, summary, pros_text, cons_text):
    """Run the Selenium script with enhanced logging"""
    try:
        run_env = 'ec2'
        logger.info("Starting Kialo discussion creation process")
        
        # Configure Chrome options based on environment
        if run_env == 'ec2':
            logger.info("Configuring Chrome for EC2 environment")
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
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
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')

            service = Service(executable_path="/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("ChromeDriver initialized successfully")
        else:
            chrome_options = Options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome service & driver instantiated")

        # Format pros and cons
        pros_text = remove_numbering_and_format(pros_text)
        cons_text = remove_numbering_and_format(cons_text)
        
        cons = split_pros_cons(cons_text)
        pros = split_pros_cons(pros_text)
        
        # Ensure we have enough pros and cons
        if len(cons) < 3:
            cons += [''] * (3 - len(cons))
        if len(pros) < 3:
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

        # Set up WebDriverWait
        wait = WebDriverWait(driver, 10)

        # Navigate to Kialo
        driver.get("https://www.kialo.com/")
        logger.info("Navigating to Kialo website")

        # Set Kialo credentials - hardcoded for now
        kialo_username = 'explore@datawithalex.com'
        kialo_password = '%Mineguy29'

        # Login process
        logger.info("Starting Kialo authentication")
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

        username_field.send_keys(kialo_username)
        password_field.send_keys(kialo_password)
        login_button.click()
        logger.info("Successfully authenticated with Kialo")

        # Wait for login to complete
        time.sleep(3)

        # Create new discussion
        new_discussion_button = wait_and_find_element(driver, By.XPATH, '//button[@aria-label="New Discussion"]')
        ActionChains(driver).move_to_element(new_discussion_button).click().perform()
        logger.info("Creating new discussion")

        # Set discussion settings
        private_option = wait_and_find_element(driver, By.CLASS_NAME, 'radio-option__input')
        ActionChains(driver).move_to_element(private_option).click().perform()
        logger.info("Selected private discussion option")

        # Navigate through setup
        next_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')
        ActionChains(driver).move_to_element(next_button).click().perform()
        logger.info("Proceeding to next step")

        # Set title and thesis
        name_field = wait_and_find_element(driver, By.CLASS_NAME, 'input-field__text-input')
        name_field.clear()
        name_field.send_keys(title)
        
        thesis_field = wait_and_find_element(driver, By.CLASS_NAME, 'top-node-text-editor__editor')
        thesis_field.clear()
        thesis_field.send_keys(bill_summary_text[:100])  # Use first 100 chars of summary as thesis
        logger.info("Added title and thesis")

        # Continue setup
        next_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')
        ActionChains(driver).move_to_element(next_button).click().perform()

        next_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')
        ActionChains(driver).move_to_element(next_button).click().perform()

        # Upload image
        script_directory = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_directory, 'image.png')
        logger.info(f"Uploading image from {image_path}")

        file_input = wait_and_find_element(driver, By.CSS_SELECTOR, "input[type='file'][data-testid='image-upload-input-element']")
        driver.execute_script("""
            arguments[0].style.height='1px';
            arguments[0].style.width='1px';
            arguments[0].style.opacity=1;
            arguments[0].removeAttribute('hidden');
        """, file_input)

        file_input.send_keys(image_path)
        logger.info("Image uploaded successfully")

        # Add tags
        tags_input_field = wait_and_find_element(driver, By.CSS_SELECTOR, "input.pill-editor-input")
        tags_input_field.clear()
        tags_input_field.send_keys("DDP")
        tags_input_field.send_keys(Keys.ENTER)
        logger.info("Added DDP tag")

        # Continue to next steps
        next_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')
        ActionChains(driver).move_to_element(next_button).click().perform()

        create_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Create")]')
        ActionChains(driver).move_to_element(create_button).click().perform()
        logger.info("Created discussion")

        # Wait for discussion to be created and get URL
        time.sleep(5)
        current_url = driver.current_url
        discussion_id = current_url.split('/')[-1]
        edit_url = f"{current_url}?path={discussion_id}.0~{discussion_id}.3&active=~{discussion_id}.3&action=edit"
        
        # Navigate to edit URL
        driver.get(edit_url)
        logger.info("Navigating to edit page")
        time.sleep(2)

        # Add bill summary
        bill_summary_elem = wait_and_find_element(driver, By.XPATH, '//p[contains(@class, "notranslate")]')
        bill_summary_elem.clear()
        bill_summary_elem.send_keys(bill_summary_text)
        logger.info("Added bill summary")

        # Save summary
        save_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "save")]')
        ActionChains(driver).move_to_element(save_button).click().perform()

        confirm_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')
        ActionChains(driver).move_to_element(confirm_button).click().perform()

        # Add pros
        logger.info("Adding pro arguments")
        for i, pro_text in enumerate([pros_1, pros_2, pros_3], 1):
            if not pro_text:
                continue
                
            logger.info(f"Adding pro argument {i}")
            add_pro_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@aria-label, "Add a new pro claim")]')
            ActionChains(driver).move_to_element(add_pro_button).click().perform()

            pro_field = wait_and_find_element(driver, By.XPATH, '//p[contains(@class, "notranslate")]')
            pro_field.clear()
            pro_field.send_keys(pro_text)

            save_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "save")]')
            ActionChains(driver).move_to_element(save_button).click().perform()
            time.sleep(1)

        # Add cons
        logger.info("Adding con arguments")
        for i, con_text in enumerate([cons_1, cons_2, cons_3], 1):
            if not con_text:
                continue
                
            logger.info(f"Adding con argument {i}")
            add_con_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@aria-label, "Add a new con claim")]')
            ActionChains(driver).move_to_element(add_con_button).click().perform()

            con_field = wait_and_find_element(driver, By.XPATH, '//p[contains(@class, "notranslate")]')
            con_field.clear()
            con_field.send_keys(con_text)

            save_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "save")]')
            ActionChains(driver).move_to_element(save_button).click().perform()
            time.sleep(1)

        # Get share link and publish
        share_link = wait_and_find_element(driver, By.XPATH, "//a[contains(@class,'share-discussion-button')]")
        kialo_discussion_url = share_link.get_attribute('href')
        logger.info(f"Navigating to Kialo Discussion URL: {kialo_discussion_url}")

        # Navigate to sharing page
        driver.get(kialo_discussion_url)
        time.sleep(2)

        # Publish discussion
        publish_button = wait_and_find_element(driver, By.XPATH, "//button[@aria-label='Publish Discussion']")
        ActionChains(driver).move_to_element(publish_button).click().perform()

        # Navigate through publish wizard
        for _ in range(2):
            next_button = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')
            ActionChains(driver).move_to_element(next_button).click().perform()
            time.sleep(1)

        publish_final = wait_and_find_element(driver, By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Publish")]')
        ActionChains(driver).move_to_element(publish_final).click().perform()

        # Get final URL
        time.sleep(2)
        final_url = driver.current_url
        clean_final_url = clean_url(final_url)
        logger.info(f"Kialo URL: {clean_final_url}")

        return clean_final_url

    except Exception as e:
        logger.error(f"Error during Kialo discussion creation: {str(e)}")
        raise e

    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")