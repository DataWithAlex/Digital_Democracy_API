import requests
import logging
import json
import re
from typing import Dict, Optional
from .logger_config import logger

# Logging configuration
logging.basicConfig(level=logging.INFO)

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
    # Split the title at the colon
    parts = title.split(":")
    if len(parts) < 2:
        # If there is no colon in the title, return it as is or handle it accordingly
        return title

    # Trim whitespace and extract the bill number (e.g., "SB 2")
    bill_number = parts[0].strip()
    # Trim whitespace for the description part
    description = parts[1].strip()

    # Format the new title as "Description (Bill Number)"
    new_title = f"{description} ({bill_number})"
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

    def publish_collection_item(self, item_id: str) -> None:
        publish_endpoint = f"https://api.webflow.com/sites/{self.site_id}/publish"

        # The IDs of the items to be published need to be wrapped in an array
        data = {
            "domains": ["digitaldemocracyproject.org"],  # Your actual domain
            "itemIds": [item_id]
        }

        response = requests.post(publish_endpoint, headers=self.headers, data=json.dumps(data))
        if response.status_code in [200, 201]:
            logger.info("Collection item published successfully")
        else:
            logger.error(f"Failed to publish collection item: {response.status_code} - {response.text}")

    def create_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str) -> Optional[str]:
        slug = generate_slug(bill_details['title'])
        title = reformat_title(bill_details['title'])
        kialo_url = clean_kialo_url(kialo_url)

        if not bill_url.startswith("http://") and not bill_url.startswith("https://"):
            logger.error(f"Invalid gov-url: {bill_url}")
            return None

        logger.info(f"slug: {slug}, title: {title}, kialo_url: {kialo_url}, description: {bill_details['description']}, gov-url: {bill_url}")

        data = {
            "fields": {
                "name": title,
                "slug": slug,
                "post-body": "",
                "jurisdiction": "",
                "voatzid": "",
                "kialo-url": kialo_url,
                "gov-url": bill_url,
                "bill-score": 0.0,
                "description": bill_details['description'],
                "support": support_text,
                "oppose": oppose_text,
                "public": True,
                "_draft": False,
                "_archived": False,
                "featured": True
            }
        }

        logger.info(f"JSON Payload: {json.dumps(data, indent=4)}")

        create_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items"
        response = requests.post(create_item_endpoint, headers=self.headers, data=json.dumps(data))
        logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201]:
            item_id = response.json()['_id']
            logger.info(f"Collection item created successfully, ID: {item_id}")
            self.publish_collection_item(item_id)
            logger.info(f"https://digitaldemocracyproject.org/bills/{slug}")
            return item_id, slug
        else:
            logger.error(f"Failed to create collection item: {response.status_code} - {response.text}")
            return None

    def update_collection_item(self, item_id: str, data: Dict) -> bool:
        update_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}"

        # Debugging: Print the JSON payload to verify the structure before sending
        logger.info(f"JSON Payload: {json.dumps(data, indent=4)}")

        # Making the PUT request to update the collection item
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
