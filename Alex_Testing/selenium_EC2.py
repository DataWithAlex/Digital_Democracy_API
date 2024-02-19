# Import Selenium components
from test_selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.common.keys import 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import time

from test_selenium import webdriver
from selenium.webdriver.chrome.options import Options



chrome_options = Options()
chrome_options.add_argument("--headless")  # Ensure GUI is off
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})


service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)


# Set the environment variables in the notebook for the current session
os.environ['KIALO_USERNAME'] = 'explore@datawithalex.com'
os.environ['KIALO_PASSWORD'] = '%Mineguy29'

# Initialize WebDriver
#service = Service(ChromeDriverManager().install())
#driver = webdriver.Chrome(service=service)

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

# Type in the credentials and log in
username_field.send_keys(username)
password_field.send_keys(password)
login_button.click()

# Wait for and click the 'New Discussion' button after logging in
new_discussion_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="New Discussion"]')))
new_discussion_button.click()

wait = WebDriverWait(driver, 10)
#element = wait.until(EC.element_to_be_clickable((By.ID, '13')))
# Wait for the radio button with a specific name attribute to be clickable and click it
# Wait for the radio button to be clickable by class name and click it
element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'radio-option__input')))
element.click()


# Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
# Find and click the 'Next' button
next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
next_button.click()

name = "Test"

# Wait for the 'Name' input field to be clickable and fill it out
#name_field = wait.until(EC.element_to_be_clickable((By.ID, 'input-field-14')))
#name_field.send_keys(name)

# Wait for the 'Name' field to be available and fill it out
name_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'input-field__text-input')))
name_field.send_keys("SB 406")

# Wait for the 'Thesis' field to be available and fill it out
# You might need to adjust the class name if it's different for the 'Thesis' field
thesis_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'top-node-text-editor__editor')))
thesis_field.send_keys("Test Thesis")


# Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
# Find and click the 'Next' button
next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
next_button.click()

# Note: Assuming 'Next' button needs to be clicked if changing the option or for the form submission.
# Find and click the 'Next' button
next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "icon-button") and contains(@aria-label, "Next")]')))
next_button.click()

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
bill_summary_text = "This is the summary of the bill that needs to be added to the text area."

time.sleep(1)
#bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(@class, "notranslate") and contains(@dir, "auto")]')))
bill_summary = wait.until(EC.element_to_be_clickable((By.XPATH, '//p[contains(text(), "Test Thesis")]')))
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

pro_1 = "pro 1"

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

pro_2 = "pro 2"

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

pro_3 = "pro 3"

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

con_1 = "con 1"

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

con_2 = "con 2"

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

con_3 = "con 3"

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

logs = driver.get_log("browser")
print(logs)
