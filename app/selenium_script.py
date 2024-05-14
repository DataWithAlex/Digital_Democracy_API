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

def split_pros_cons(text):
    pattern = r'\d+\)\s'
    matches = list(re.finditer(pattern, text))
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
    
    if run_env == 'ec2':
        logger.info("Running in EC2 environment.")
        
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
        logger.info("ChromeDriver initialized successfully")
        
    else:
        logger.info("Running in local environment.")
        chrome_options = Options()
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("chrome service & driver instantiated")

    os.environ['KIALO_USERNAME'] = 'explore@datawithalex.com'
    os.environ['KIALO_PASSWORD'] = '%Mineguy29'

    cons = split_pros_cons(cons_text)
    cons_1, cons_2, cons_3 = cons[0], cons[1], cons[2]

    pros = split_pros_cons(pros_text)
    pros_1, pros_2, pros_3 = pros[0], pros[1], pros[2]

    bill_summary_text = summary
    if len(bill_summary_text) > 500:
        last_period_index = bill_summary_text.rfind('.', 0, 500)
        if last_period_index != -1:
            bill_summary_text = bill_summary_text[:last_period_index + 1]
        else:
            bill_summary_text = bill_summary_text[:500]

    driver.get("https://www.kialo.com/my")

    username = os.environ.get('KIALO_USERNAME')
    password = os.environ.get('KIALO_PASSWORD')

    wait = WebDriverWait(driver, 20)

    try:
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

        logger.info("Logging in to Kialo")
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        logger.info("Logged in to Kialo")

        new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
        new_discussion_button.click()
        logger.info("Creating Discussion")

        element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
        element.click()
        logger.info("Select Private Discussion")

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

        name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
        name_field.send_keys(title)

        thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
        thesis_field.send_keys("Test Thesis")

        logger.info("Filled out Name and Thesis")

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()
        logger.info("Next Page")

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
        logger.info("Uploaded Image")

        upload_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Drag and drop or click')]")
        upload_button.click()

        tags_input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.pill-editor-input")))
        tags_input_field.clear()
        tags_input_field.send_keys("DDP")
        tags_input_field.send_keys(Keys.ENTER)

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Create")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Enter")]')))
        next_button.click()

        time.sleep(1)
        current_url = driver.current_url
        x = current_url[-5:]
        new_url = f"{current_url}?path={x}.0~{x}.3&active=~{x}.3&action=edit"
        driver.get(new_url)

        time.sleep(1)
        bill_summary_ = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S") or contains(text(), "H") or contains(text(), "Test")]')))
        bill_summary_.clear()
        bill_summary_.send_keys(bill_summary_text)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(pros_1)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(pros_2)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(pros_3)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(cons_1)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(cons_2)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
        next_button.click()

        time.sleep(1)
        pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
        pro.clear()
        pro.send_keys(cons_3)

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
        next_button.click()

        time.sleep(1)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
        next_button.click()

        share_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@class,'share-discussion-button')]")))

        kialo_discussion_url = share_link.get_attribute('href')
        logger.info(f"Navigating to Kialo Discussion URL: {kialo_discussion_url}")

        driver.get(kialo_discussion_url)

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

        logs = driver.get_log("browser")

        with open("browser_logs.txt", "w") as file:
            for log in logs:
                log_entry = f"{log['timestamp']}: {log['level']} - {log['message']}\n"
                file.write(log_entry)
    
        current_url = driver.current_url
        modified_url = clean_url(current_url)
        logger.info(f"Kialo URL: {modified_url}")
        driver.quit()

        return modified_url

    except (TimeoutException, WebDriverException) as e:
        logger.error(f"An error occurred during the Selenium script execution: {e}")
        driver.quit()
        raise
