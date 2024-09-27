import openai
import logging
import json
import re
import requests
import os
from typing import Dict, Optional
from .logger_config import logger

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Define OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

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

# Function to get the top 3 categories using GPT-4o
def get_top_categories(bill_text, categories, model="gpt-4o"):
    system_message = (
        "You are an AI that categorizes legislative texts into predefined categories. "
        "You will receive a list of categories and the text of a legislative bill. "
        "Your task is to select the three most relevant categories for the given text."
    )
    
    categories_list = "\n".join([f"- {category['name']}" for category in categories])
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

# Function to format the OpenAI output for Webflow
def format_categories_for_webflow(openai_output, valid_categories):
    category_ids = []
    valid_category_ids = {category["id"] for category in valid_categories}
    
    for category in openai_output:
        parts = category.strip("[]").split(",")
        if len(parts) == 2:
            category_id = parts[1].strip()
            if category_id in valid_category_ids:
                category_ids.append(category_id)
            else:
                logging.warning(f"Invalid Category ID detected: {category_id}")
    
    return category_ids

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

    def create_live_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str, jurisdiction: str) -> Optional[str]:
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

        # Generate categories based on the bill text
        bill_text = bill_details.get("full_text", "")
        top_categories = get_top_categories(bill_text, categories)
        formatted_categories = format_categories_for_webflow(top_categories, categories)
        logger.info(f"Formatted Categories for Webflow: {formatted_categories}")

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
                "category": formatted_categories  # Set the categories field
            }
        }

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

    def update_collection_item(self, item_id: str, data: Dict) -> bool:
        update_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}"

        logger.info(f"JSON Payload: {json.dumps(data, indent=4)}")

        response = requests.put(update_item_endpoint, headers=self.headers, data=json.dumps(data))
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        return response.status_code in [200, 201]

    def get_collection_item(self, item_id: str) -> Optional[Dict]:
        get_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}"

        response = requests.get(get_item_endpoint, headers=self.headers)
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Failed to get collection item: {response.status_code} - {response.text}")
            return None