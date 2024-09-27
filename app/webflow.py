import openai
import logging
import json
import re
import requests
import os
from typing import Dict, Optional
from .logger_config import logger
from .utils import categories, get_category_ids  # Updated import statement

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Define OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to get the top 3 categories using GPT-4o
def get_top_categories(bill_text, categories, model="gpt-4o"):
    system_message = (
        "You are an AI that categorizes legislative texts into predefined categories. "
        "You will receive a list of categories and the text of a legislative bill. "
        "Your task is to select the three most relevant categories for the given text."
    )
    
    categories_list = "\n".join([f"- {category['name']}"] for category in categories)
    user_message = f"Here is a list of categories:\n{categories_list}\n\nBased on the following bill text, select the three most relevant categories:\n{bill_text}. NOTE: YOU MUST RETURN THEM IN THE FOLLOWING FORMAT: [CATEGORY: CATEGORY ID]. For example, [Disney, 655288ef928edb128306742c]"

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
    )
    
    top_categories_response = response['choices'][0]['message']['content']
    top_categories = [category.strip() for category in top_categories_response.split("\n") if category.strip()]
    
    return top_categories
# Define the list of categories with their names and IDs
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the list of categories with their names and IDs
categories = [
    {"name": "Animals", "id": "668329ae71bf22a23a6ac94b"},
    {"name": "International Relations", "id": "663299c73b94826974bd24da"},
    {"name": "National Security", "id": "6632997a194f0d20b0d24108"},
    {"name": "Civil Rights", "id": "663298e4562bd3696c89b3ea"},
    {"name": "Arts", "id": "660ede71e88a45fcd08e2e39"},
    {"name": "Energy", "id": "660ed44984debef46e8d5c5d"},
    {"name": "Military and Veterans", "id": "65ce5778dae6450ac15a2d2f"},
    {"name": "Priority Bill", "id": "65ba9dbe9768a6290a95c945"},
    {"name": "Media", "id": "65b550562534316ee17131c0"},
    {"name": "LGBT", "id": "655288ef928edb128306753e"},
    {"name": "Public Records", "id": "655288ef928edb128306753d"},
    {"name": "Social Welfare", "id": "655288ef928edb12830673e2"},
    {"name": "Technology", "id": "655288ef928edb128306743e"},
    {"name": "Government", "id": "655288ef928edb12830673e1"},
    {"name": "Business", "id": "655288ef928edb128306746b"},
    {"name": "Employment", "id": "655288ef928edb1283067425"},
    {"name": "Public Safety", "id": "655288ef928edb1283067442"},
    {"name": "Drugs", "id": "655288ef928edb128306745e"},
    {"name": "Immigration", "id": "655288ef928edb12830673e5"},
    {"name": "Transportation", "id": "655288ef928edb1283067415"},
    {"name": "Criminal Justice", "id": "655288ef928edb12830673dc"},
    {"name": "Elections", "id": "655288ef928edb12830673e0"},
    {"name": "Culture", "id": "655288ef928edb1283067436"},
    {"name": "Sports", "id": "655288ef928edb12830673df"},
    {"name": "Marriage", "id": "655288ef928edb128306742d"},
    {"name": "Housing", "id": "655288ef928edb128306743d"},
    {"name": "Education", "id": "655288ef928edb12830673e4"},
    {"name": "Medical", "id": "655288ef928edb12830673e9"},
    {"name": "State Parks", "id": "655288ef928edb128306745d"},
    {"name": "Guns", "id": "655288ef928edb128306741f"},
    {"name": "Disney", "id": "655288ef928edb128306742c"},
    {"name": "Natural Disasters", "id": "655288ef928edb1283067435"},
    {"name": "Environment", "id": "655288ef928edb128306741b"},
    {"name": "Taxes", "id": "655288ef928edb128306745c"}
]

# Create a dictionary for quick lookup
category_dict = {category["name"].lower(): category["id"] for category in categories}

def get_category_ids(category_names):
    """
    Given a list of category names, return the corresponding category IDs.
    """
    category_ids = []
    for name in category_names:
        # Convert name to lowercase to match the dictionary keys
        category_id = category_dict.get(name.lower())
        if category_id:
            category_ids.append(category_id)
            logging.info(f"Matched category '{name}' to ID '{category_id}'")
        else:
            logging.warning(f"Warning: Category '{name}' not found in predefined categories.")
    return category_ids

# Function to get the top 3 categories using GPT-4o
def get_top_categories(bill_text, categories, model="gpt-4o"):
    system_message = (
        "You are an AI that categorizes legislative texts into predefined categories. "
        "You will receive a list of categories and the text of a legislative bill. "
        "Your task is to select the three most relevant categories for the given text."
    )

    # Properly formatting categories list for OpenAI input
    categories_list = "\n".join([f"- {category['name']}"] for category in categories)
    user_message = f"Here is a list of categories:\n{categories_list}\n\nBased on the following bill text, select the three most relevant categories:\n{bill_text}. NOTE: YOU MUST RETURN THEM IN THE FOLLOWING FORMAT: [CATEGORY: CATEGORY ID]. For example, [Disney, 655288ef928edb128306742c]"

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
    )

    top_categories_response = response['choices'][0]['message']['content']

    # Debug logging the response
    logger.info(f"OpenAI Category Response: {top_categories_response}")

    # Splitting the response and stripping to clean any extraneous spaces/newlines
    top_categories = [category.strip() for category in top_categories_response.split("\n") if category.strip()]

    return top_categories
# webflow.py

# Update the `format_categories_for_webflow` function
def format_categories_for_webflow(openai_output):
    """
    Formats the OpenAI output for Webflow by extracting valid category IDs.

    Parameters:
    - openai_output (list): A list of category names and IDs returned by OpenAI.

    Returns:
    - list: A list of valid category IDs that match the categories in the OpenAI output.
    """
    # Initialize an empty list to store valid category IDs
    category_ids = []

    # Debug log the OpenAI output
    logger.info(f"OpenAI Output Before Formatting: {openai_output}")

    # Iterate through each line of the OpenAI output
    for category in openai_output:
        # Extract text within square brackets (e.g., [Public Safety: d8856afc5a46364392334030])
        match = re.search(r'\[(.+?): (.+?)\]', category)
        if match:
            # Extract category name and ID
            category_name, category_id = match.groups()

            # Verify if the category ID exists in the predefined categories
            if category_id in category_dict.values():
                category_ids.append(category_id)
                logger.info(f"Matched category '{category_name}' to ID '{category_id}'")
            else:
                logging.warning(f"Warning: Category ID '{category_id}' not found in predefined categories.")
        else:
            logging.warning(f"Warning: OpenAI output '{category}' does not match the expected format.")

    # If category_ids is empty, log the issue for further debugging
    if not category_ids:
        logger.error(f"Failed to format OpenAI output correctly: {openai_output}")

    return category_ids


# Example usage for testing/debugging purposes
openai_output = [
    '[Public Safety: d8856afc5a46364392334030]',
    '[Government: 655288ef928edb12830673e1]',
    '[Transportation: 655288ef928edb1283067415]'
]

# Format the output for Webflow
formatted_categories = format_categories_for_webflow(openai_output)
print(f"Formatted Categories for Webflow: {formatted_categories}")


def generate_slug(title):
    # Convert to lowercase
    slug = title.lower()
    # Replace spaces with hyphens
    slug = slug.replace(" ", "-")
    # Remove invalid characters
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug

def reformat_title(title):
    """
    Reformat the title to include only the bill type and number in parentheses.
    For example, convert "118 HR 9056 IH: VA Insurance Improvement Act" to 
    "VA Insurance Improvement Act (HR 9056)".
    """
    # Split the title at the colon to separate the bill identifier and description
    parts = title.split(":")
    
    if len(parts) < 2:
        # If there is no colon in the title, return it as is
        return title

    # Trim whitespace and extract the bill identifier (e.g., "118 HR 9056 IH")
    bill_identifier = parts[0].strip()
    # Extract only the description part
    description = parts[1].strip()
    
    # Use a regular expression to find the bill type and number
    # This will match patterns like "HR 9056" or "S 3187"
    match = re.search(r'([A-Z]+) (\d+)', bill_identifier)
    
    if not match:
        # If the pattern is not found, return the original title
        return title

    # Extract the bill type and number
    bill_type, bill_number = match.groups()

    # Format the new title as "Description (Bill Type Number)"
    new_title = f"{description} ({bill_type} {bill_number})"
    return new_title

def clean_kialo_url(url: str) -> str:
    # Split the URL at "&action="
    parts = url.split("&action=")
    # Return the first part which contains the URL without the action parameter
    return parts[0]


class WebflowAPI:
    def __init__(self, api_key: str, collection_id: str, site_id: str):
        self.api_key = api_key
        self.collection_id = collection_id
        self.site_id = site_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'accept-version': '1.0.0',
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        self.base_url = "https://api.webflow.com"
        self.jurisdiction_map = {
            'FL': '655288ef928edb128306745f',
            'US': '65810f6b889af86635a71b49'
        }


    def create_live_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str, jurisdiction: str, formatted_categories: list) -> Optional[str]:
        slug = generate_slug(bill_details['title'])
        title = reformat_title(bill_details['title'])
        kialo_url = clean_kialo_url(kialo_url)

        if not bill_url.startswith("http://") and not bill_url.startswith("https://"):
            logger.error(f"Invalid gov-url: {bill_url}")
            return None

        jurisdiction_item_ref = self.jurisdiction_map.get(jurisdiction)
        if not jurisdiction_item_ref:
            logger.error(f"Invalid jurisdiction: {jurisdiction}")
            return None

        # Use the formatted categories passed as a parameter
        data = {
            "isArchived": False,
            "isDraft": False,
            "fieldData": {
                "name": title,
                "slug": slug,
                "post-body": bill_text,  # Include bill text in the post-body field
                "jurisdiction": jurisdiction_item_ref,
                "voatzid": "",
                "kialo-url": kialo_url,
                "gov-url": bill_url,
                "bill-score": 0.0,
                "description": bill_details['description'],
                "support": support_text,
                "oppose": oppose_text,
                "public": True,
                "featured": True,
                "category": formatted_categories  # Use formatted categories here
            }
        }

        # Log the final payload
        logger.info(f"JSON Payload: {json.dumps(data, indent=4)}")

        create_item_endpoint = f"{self.base_url}/v2/collections/{self.collection_id}/items/live"
        response = requests.post(create_item_endpoint, headers=self.headers, json=data)
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201, 202]:
            item_id = response.json().get('id')
            logger.info(f"Live collection item created successfully, ID: {item_id}")
            return item_id, slug
        else:
            logger.error(f"Failed to create live collection item: {response.status_code} - {response.text}")
            return None


    def get_collection_item(self, item_id: str) -> Optional[Dict]:
        get_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}"

        response = requests.get(get_item_endpoint, headers=self.headers)
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Failed to get collection item: {response.status_code} - {response.text}")
            return None