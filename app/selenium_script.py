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

# Configure logging to only show INFO level messages and suppress all debug logs
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Only show the message without timestamp or level
)
logger = logging.getLogger(__name__)

# Disable all selenium and urllib3 logging
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.ERROR)

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
        logger.info("✓ Logged in to Kialo")

        # Create new discussion
        new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
        new_discussion_button.click()
        logger.info("✓ Started new discussion")

        # Select Private Discussion
        element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
        element.click()
        logger.info("✓ Set discussion to private")

        # Click Next
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

        # Fill out Name and Thesis
        name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
        name_field.send_keys(title)

        thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
        thesis_field.send_keys("Test Thesis")
        logger.info("✓ Added title and thesis")

        # Next Page
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

        # Next Page again
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

        # Upload Image
        script_directory = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_directory, 'image.png')
        logger.info(f"Uploading Image for Discussion {image_path}")

        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][data-testid='image-upload-input-element']")
        driver.execute_script("""
            arguments[0].style.height='1px';
            arguments[0].style.width='1px';
            arguments[0].style.opacity=1;
            arguments[0].removeAttribute('hidden');
        """, file_input)

        logger.info("About to upload image")
        file_input.send_keys(image_path)
        logger.info("✓ Added image")

        # Click upload button
        upload_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Drag and drop or click')]")
        upload_button.click()
        logger.info("Drag and drop or click")

        # Add DDP tag
        tags_input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.pill-editor-input")))
        tags_input_field.clear()
        tags_input_field.send_keys("DDP")
        tags_input_field.send_keys(Keys.ENTER)
        logger.info("✓ Added DDP tag")

        # Next
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next")

        # Create
        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Create")]')))
        next_button.click()
        logger.info("✓ Created discussion")

        # Wait for discussion to be created and get URL
        time.sleep(10)
        current_url = driver.current_url
        x = current_url[-5:]
        new_url = f"{current_url}?path={x}.0~{x}.3&active=~{x}.3&action=edit"
        driver.get(new_url)
        logger.info("Edit")
        logger.info(new_url)

        # Add Bill Summary
        time.sleep(1)
        bill_summary_ = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S") or contains(text(), "H") or contains(text(), "Thesis")]')))
        bill_summary_.clear()
        bill_summary_.send_keys(bill_summary_text)
        logger.info("✓ Added bill summary")

        # Save
        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        # Confirm
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')))
        next_button.click()

        # Add Pros
        pros_added = 0
        for pro_text in [pros_1, pros_2, pros_3]:
            if pro_text.strip():
                time.sleep(1)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
                next_button.click()

                time.sleep(1)
                pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
                pro.clear()
                pro.send_keys(pro_text)

                time.sleep(1)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
                next_button.click()
                pros_added += 1
        logger.info(f"✓ Added {pros_added} supporting arguments")

        # Add Cons
        cons_added = 0
        for con_text in [cons_1, cons_2, cons_3]:
            if con_text.strip():
                time.sleep(1)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
                next_button.click()

                time.sleep(1)
                con = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
                con.clear()
                con.send_keys(con_text)

                time.sleep(1)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
                next_button.click()
                cons_added += 1
        logger.info(f"✓ Added {cons_added} opposing arguments")

        # Get share link and publish
        share_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@class,'share-discussion-button')]")))
        kialo_discussion_url = share_link.get_attribute('href')
        logger.info(f"Navigating to Kialo Discussion URL: {kialo_discussion_url}")

        driver.get(kialo_discussion_url)

        # Publish Discussion
        time.sleep(1)
        share_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Publish Discussion']")))
        share_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Publish")]')))
        next_button.click()

        # Get final URL and clean it
        current_url = driver.current_url
        modified_url = clean_url(current_url)
        logger.info(f"✓ Discussion created at: {modified_url}")
        
        if driver:
            driver.quit()
        return modified_url

    except (TimeoutException, WebDriverException) as e:
        logger.error(f"❌ Failed to create discussion: {str(e)}")
        if driver:
            driver.quit()
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        if driver:
            driver.quit()
        return None