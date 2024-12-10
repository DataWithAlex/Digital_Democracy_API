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
from .logger_config import selenium_logger

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

def run_selenium_script(pros, cons, bill_text, bill_id=None):
    """Run the Selenium script with enhanced logging"""
    try:
        selenium_logger.info("Starting Selenium script", extra={
            'bill_id': bill_id,
            'pros_count': len(pros.split('\n')),
            'cons_count': len(cons.split('\n'))
        })
        
        # Initialize Chrome options with logging
        selenium_logger.info("Configuring Chrome options")
        chrome_options = webdriver.ChromeOptions()
        # ... rest of chrome options ...
        
        # Initialize driver
        selenium_logger.info("Initializing Chrome driver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Login to Kialo
            selenium_logger.info("Attempting Kialo login")
            driver.get("https://www.kialo.com/login")
            # ... rest of login code ...
            
            # Create discussion
            selenium_logger.info("Creating Kialo discussion")
            # ... discussion creation code ...
            
            # Add content
            selenium_logger.info("Adding content to discussion")
            # ... content addition code ...
            
            # Get URL
            kialo_url = driver.current_url
            selenium_logger.info("Successfully created Kialo discussion", 
                               extra={'kialo_url': kialo_url})
            
            return kialo_url
            
        except Exception as e:
            selenium_logger.error(f"Selenium operation failed: {str(e)}", exc_info=True)
            raise
        finally:
            selenium_logger.info("Closing Chrome driver")
            driver.quit()
            
    except Exception as e:
        selenium_logger.error(f"Selenium script failed: {str(e)}", exc_info=True)
        raise