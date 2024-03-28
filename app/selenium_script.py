# Import Selenium components
# from test_selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.common.keys import 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import time
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re
import logging

# selenium_script.py
# from .logger_config import get_logger
#from .logger_config import logger
from .logger_config import logger

# Logging configuration
logging.basicConfig(level=logging.INFO)


def split_pros_cons(text):
    # Regular expression pattern to match the numbered points
    pattern = r'\d+\)\s'
    # Find all matches and their positions
    matches = list(re.finditer(pattern, text))
    sections = []
    
    # Split the text based on the positions of the matches
    for i, match in enumerate(matches):
        start = match.start()
        # If it's not the last match, the end is the start of the next match
        if i < len(matches) - 1:
            end = matches[i + 1].start()
            sections.append(text[start:end].strip())
        else:
            # For the last match, the end is the end of the text
            sections.append(text[start:].strip())
    
    return sections

import os

def clean_url(url):
    # Split the URL by "/permissions" and take the first part
    cleaned_url = url.split("/permissions")[0] + "/"
    return cleaned_url


def run_selenium_script(title, summary, pros_text, cons_text):
#    chrome_options = Options()
#    # chrome_options.add_argument("--headless")
#    chrome_options.add_argument("--no-sandbox")
#    chrome_options.add_argument("--disable-dev-shm-usage")

#    # Initialize the Chrome driver with the specified options
#    service = Service(ChromeDriverManager().install())
#    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    #logger.info(f"Before accessing RUN_ENV, checking environment: {os.getenv('RUN_ENV')}")
    #run_env = 'os.getenv('RUN_ENV', 'local').lower()'
    #logger.info(f"Accessed RUN_ENV: {run_env}")

    # DETERMINE VARIABLES HERE
    run_env = 'ec2'
    #run_env = 'local'

    #run_env = os.getenv('RUN_ENV', 'local').lower()
    #print(f"Current RUN_ENV: {run_env}")
    #logger.info(f"Current RUN_ENV: {run_env}")
    #run_env = os.getenv("RUN_ENV")

    if run_env == 'ec2':
        print("Running in EC2 environment.")
        logger.info("Selenium Confirmed to be running on EC2")
        # EC2 specific code here
        # Example: Adjust Selenium ChromeDriver options for EC2
        logger.info("Initializing ChromeDriver with headless options")
        # Specify Chrome options for headless execution
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

        # Log the confirmation of chrome options
        logger.info("Chrome options: --headless --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1920,1080 --remote-debugging-port=9222 --disable-extensions --disable-setuid-sandbox --disable-infobars confirmed")

        # Update the path to where your ChromeDriver is located
        service = Service("/home/ec2-user/.wdm/drivers/chromedriver/linux64/121.0.6167.184/chromedriver-linux64/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)

        logger.info("ChromeDriver initialized successfully")
        # Setup for WebDriver (Chrome) with the specified options

        #service = Service("/home/ec2-user/.wdm/drivers/chromedriver/linux64/121.0.6167.184/chromedriver-linux64/chromedriver")
        #driver = webdriver.Chrome(service=service)

        #service = Service("/usr/bin/chromedriver")
        #driver = webdriver.Chrome(service=service, options=chrome_options)

        logger.info("chrome service & driver instantiated")
    else:
        print("Running in local environment.")
        logger.info("Selenium Confirmed to be running on Local @run_selenium_script")
        # Local specific code here
        # Example: Setup Selenium for local development, possibly without headless mode
        chrome_options = Options()
        logger.info("chrome options confirmed")
        # chrome_options.add_argument("--headless")  # Uncomment if you want headless in local too
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("chrome service & driver instantiated")

    # Set the environment variables in the notebook for the current session
    os.environ['KIALO_USERNAME'] = 'explore@datawithalex.com'
    os.environ['KIALO_PASSWORD'] = '%Mineguy29'

    # Initialize WebDriver
    #service = Service(ChromeDriverManager().install())
    #driver = webdriver.Chrome(service=service)

    cons = split_pros_cons(cons_text)
    con_1, con_2, con_3 = cons[0], cons[1], cons[2]

    pros = split_pros_cons(pros_text)
    pro_1, pro_2, pro_3 = pros[0], pros[1], pros[2]

    # title = "HB 23: Water and Wastewater Facility Operators"
    bill_summary_text = summary
    if len(bill_summary_text) > 500:
        bill_summary_text = bill_summary_text[:500]

    # Navigate to the Kialo login page
    driver.get("https://www.kialo.com/my")

    # Retrieve credentials from environment variables
    username = os.environ.get('KIALO_USERNAME')
    password = os.environ.get('KIALO_PASSWORD')

    # Wait for the login elements to load
    wait = WebDriverWait(driver, 10)

    # Find the username and password fields and the login button
    username_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrUsername")))
    password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Log In"]')))

    logger.info("Logging in to Kialo")
    # Type in the credentials and log in
    username_field.send_keys(username)
    password_field.send_keys(password)
    login_button.click()

    logger.info("Logged in to Kialo")

    # Wait for and click the 'New Discussion' button after logging in
    new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
    new_discussion_button.click()
    logger.info("Creating Discussion")

    wait = WebDriverWait(driver, 10)
    #element = wait.until(EC.element_to_be_clickable((By.ID, '13')))
    # Wait for the radio button with a specific name attribute to be clickable and click it
    # Wait for the radio button to be clickable by class name and click it
    element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
    element.click()
    logger.info("Select Private Discussion")

    #public_radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='radio'][@data-id='1']")))
    #public_radio_button.click()


    # Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
    # Find and click the 'Next' button
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
    next_button.click()
    logger.info("Next Page")

    name = "Test"

    # Wait for the 'Name' input field to be clickable and fill it out
    #name_field = wait.until(EC.element_to_be_clickable((By.ID, 'input-field-14')))
    #name_field.send_keys(name)

    # Wait for the 'Name' field to be available and fill it out
    name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
    name_field.send_keys(title)

    # Wait for the 'Thesis' field to be available and fill it out
    # You might need to adjust the class name if it's different for the 'Thesis' field
    thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
    thesis_field.send_keys("Test Thesis")

    logger.info("Filled our Name and Thesis")

    # Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
    # Find and click the 'Next' button
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
    next_button.click()

    logger.info("Next Page")

    # Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
    # Find and click the 'Next' button
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
    next_button.click()
    logger.info("Next Page")

    ### HERE we are in the file upload section

    #import os

    # Get the absolute path to the image file
    #image_path = os.path.abspath('/Users/alexsciuto/Library/Mobile Documents/com~apple~CloudDocs/DataWithAlex/ddp-api/Digital_Democracy_API/image.png')
    # Get the directory of the current script file. This works even if you run the script from a different directory
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Now, construct the path to the image.png assuming it's in the same directory as this script
    image_path = os.path.join(script_directory, 'image.png')

    logger.info(f"Uploading Image for Discussion {image_path}")

    # Locate the file input element which is likely hidden
    file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file'][data-testid='image-upload-input-element']")

    # Before interacting, make sure the input is interactable by removing any 'hidden' attributes or styles via JavaScript
    driver.execute_script("""
        arguments[0].style.height='1px';
        arguments[0].style.width='1px';
        arguments[0].style.opacity=1;
        arguments[0].removeAttribute('hidden');
    """, file_input)

    logger.info(f"About to upload image")

    # Now, send the file path to the file input element, this should open the file selector dialog and select the file
    file_input.send_keys(image_path)

    logger.info(f"Uploaded Image")

    # Some applications rely on change events to detect when a file has been selected
    # Trigger the change event just in case the application needs it
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { 'bubbles': true }));", file_input)

    # If there is a button that needs to be clicked to finalize the upload after the file is selected, do that here.
    # You mentioned the aria-label contains "Drag and drop or click" for the upload element,
    # so if needed, find that element and click it to initiate the upload.
    upload_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Drag and drop or click')]")
    upload_button.click()

    # Note: The final click on the 'upload_button' might not be necessary if the application starts uploading immediately after the file selection.

    ###
    logger.info(f"About to add tags")

        # Wait for the tags input field to be clickable
    tags_input_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.pill-editor-input")))

    # Clear the input field in case there's any pre-filled text
    tags_input_field.clear()

    # Enter the text "DDP" into the input field
    tags_input_field.send_keys("DDP")

    # To submit the tag, you would typically press Enter or click an add button.
    # If pressing Enter submits the tag, use this line:
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
    # Get the current URL
    current_url = driver.current_url

    # Extract the last 5 characters assuming they are the required digits
    x = current_url[-5:]

    # Construct the new URL with the required format
    new_url = f"{current_url}?path={x}.0~{x}.3&active=~{x}.3&action=edit"

    # Print the new URL to check
    driver.get(new_url)

    # Variable containing the summary you want to add
    # bill_summary_text = "This is the summary of the bill that needs to be added to the text area."

    time.sleep(1)
    #bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    #bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S")]')))
    bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "S") or contains(text(), "H")]')))

    #bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "Test Thesis")]')))

    bill_summary.clear()
    bill_summary.send_keys(bill_summary_text)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button") and contains(@aria-label, "Confirm")]')))
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #pro_1 = "pro 1"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(pro_1)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #pro_2 = "pro 2"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(pro_2)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new pro claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #pro_3 = "pro 3"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(pro_3)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #con_1 = "con 1"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(con_1)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #con_2 = "con 2"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(con_2)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
    next_button.click()

    #con_3 = "con 3"

    time.sleep(1)
    pro = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
    pro.clear()
    pro.send_keys(con_3)

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "save") and contains(@aria-label, "Save")]')))
    time.sleep(1)
    next_button.click()

    time.sleep(1)
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Add a new con claim") and contains(@class, "hoverable")]')))
    next_button.click()

    time.sleep(1)
    # Wait for the button with the specific aria-label to be clickable and click it
    share_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Share']")))
    share_button.click()

    time.sleep(1)
    # Wait for the button with the specific aria-label to be clickable and click it
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

    # Retrieve the logs
    logs = driver.get_log("browser")

    # Save the logs to a file
    with open("browser_logs.txt", "w") as file:
        for log in logs:
            # Example of formatting the log entry as a string before writing it
            log_entry = f"{log['timestamp']}: {log['level']} - {log['message']}\n"
            file.write(log_entry)
    
    
    current_url = driver.current_url
    modified_url = clean_url(current_url)
    print("Modified URL:", modified_url)
    logger.info(f"here is the Kialo URL:{modified_url}")
    logger.info("*** EXITING selenium_script.py ***")

    driver.quit()

    return modified_url
    



# Don't forget to quit the driver session
