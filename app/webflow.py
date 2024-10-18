import openai
import logging
import json
import re
import requests
import os
from typing import Dict, Optional
from .logger_config import logger
from .utils import categories, category_dict

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Define OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_top_categories(bill_text, categories, model="gpt-4"):
    system_message = (
        "You are an AI that categorizes legislative texts into predefined categories. "
        "You will receive a list of categories and the text of a legislative bill. "
        "Your task is to select the three most relevant categories for the given text."
    )

    categories_list = "\n".join([f"- {category['name']}: {category['id']}" for category in categories])
    user_message = f"Here is a list of categories:\n{categories_list}\n\nBased on the following bill text, select the three most relevant categories:\n{bill_text}\nNOTE: YOU MUST RETURN THEM IN THE FOLLOWING FORMAT: [Category Name: Category ID]. For example, [Disney: 655288ef928edb128306742c]"

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


def format_categories_for_webflow(openai_output, predefined_categories):
    formatted_categories = []
    category_pattern = re.compile(r'\[?(.*?)\s*:\s*(.*?)\]?')
    for line in openai_output:
        matches = category_pattern.findall(line)
        if not matches:
            logger.warning(f"Warning: Could not parse categories from line '{line}'")
            continue
        for match in matches:
            category_name = match[0].strip()
            category_id = match[1].strip()
            if category_id in predefined_categories.values():
                formatted_categories.append(category_id)
            else:
                logger.warning(f"Warning: Category ID '{category_id}' not found in predefined categories.")
    return formatted_categories

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

    def create_live_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str, jurisdiction: str, formatted_categories: list) -> Optional[tuple]:
        logger.info("Preparing to create Webflow collection item...")
        slug = generate_slug(bill_details['title'])
        title = reformat_title(bill_details['title'])
        kialo_url = clean_kialo_url(kialo_url)
        bill_text = bill_details.get('full_text', '')

        logger.info(f"Slug generated: {slug}, Title formatted: {title}, Bill text: {len(bill_text)} characters.")

        if not bill_url.startswith("http://") and not bill_url.startswith("https://"):
            logger.error(f"Invalid gov-url: {bill_url}")
            return None

        jurisdiction_item_ref = self.jurisdiction_map.get(jurisdiction)
        if not jurisdiction_item_ref:
            logger.error(f"Invalid jurisdiction: {jurisdiction}")
            return None

        data = {
            "fields": {
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
                "category": formatted_categories,  # Use formatted categories here
                "_draft": False,
                "_archived": False
            }
        }

        # Log the final payload
        logger.info(f"JSON Payload for Webflow: {json.dumps(data, indent=4)}")

        # Make the API request to Webflow
        create_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items?live=true"
        response = requests.post(create_item_endpoint, headers=self.headers, json=data)
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201, 202]:
            item = response.json().get('item')
            item_id = item.get('_id')
            slug = item.get('slug')
            logger.info(f"Live collection item created successfully. ID: {item_id}, Slug: {slug}")
            return item_id, slug
        else:
            logger.error(f"Failed to create live collection item. Status: {response.status_code}, Response: {response.text}")
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

    def update_collection_item(self, item_id: str, data: Dict) -> bool:
        update_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}?live=true"

        response = requests.put(update_item_endpoint, headers=self.headers, json=data)
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201, 202]:
            logger.info(f"Collection item updated successfully, ID: {item_id}")
            return True
        else:
            logger.error(f"Failed to update collection item: {response.status_code} - {response.text}")
            return False