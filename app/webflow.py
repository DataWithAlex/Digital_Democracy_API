import requests
import logging
import json
import re
from typing import Dict, Optional
from .logger_config import logger
from .bill_processing import categorize_bill

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

# Function to map category names to Webflow category IDs
def map_category_to_id(category_name):
    category_mapping = {
        "Animals": "668329ae71bf22a23a6ac94b",
        "International Relations": "663299c73b94826974bd24da",
        "National Security": "6632997a194f0d20b0d24108",
        "Civil Rights": "663298e4562bd3696c89b3ea",
        "Arts": "660ede71e88a45fcd08e2e39",
        "Energy": "660ed44984debef46e8d5c5d",
        "Military and Veterans": "65ce5778dae6450ac15a2d2f",
        "Priority Bill": "65ba9dbe9768a6290a95c945",
        "Media": "65b550562534316ee17131c0",
        "LGBT": "655288ef928edb128306753e",
        "Public Records": "655288ef928edb128306753d",
        "Social Welfare": "655288ef928edb12830673e2",
        "Technology": "655288ef928edb128306743e",
        "Government": "655288ef928edb12830673e1",
        "Business": "655288ef928edb128306746b",
        "Employment": "655288ef928edb1283067425",
        "Public Safety": "655288ef928edb1283067442",
        "Drugs": "655288ef928edb128306745e",
        "Immigration": "655288ef928edb12830673e5",
        "Transportation": "655288ef928edb1283067415",
        "Criminal Justice": "655288ef928edb12830673dc",
        "Elections": "655288ef928edb12830673e0",
        "Culture": "655288ef928edb1283067436",
        "Sports": "655288ef928edb12830673df",
        "Marriage": "655288ef928edb128306742d",
        "Housing": "655288ef928edb128306743d",
        "Education": "655288ef928edb12830673e4",
        "Medical": "655288ef928edb12830673e9",
        "State Parks": "655288ef928edb128306745d",
        "Guns": "655288ef928edb128306741f",
        "Disney": "655288ef928edb128306742c",
        "Natural Disasters": "655288ef928edb1283067435",
        "Environment": "655288ef928edb128306741b",
        "Taxes": "655288ef928edb128306745c"
    }
    return category_mapping.get(category_name)


def reformat_title(title):
    """
    Reformat the title to exclude the congressional session and other suffixes.
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
    
    # Extract the bill type and number (e.g., "HR 9056") without session or suffixes
    bill_type_number = " ".join(bill_identifier.split()[1:3])  # Takes only the second and third parts, which are the type and number

    # Format the new title as "Description (Bill Type Number)"
    new_title = f"{description} ({bill_type_number})"
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

    # Function to create a Webflow collection item
    def create_collection_item(self, bill_url, bill_details, kialo_url, support_text, oppose_text, category):
        slug = generate_slug(bill_details['title'])
        title = reformat_title(bill_details['title'])
        kialo_url = clean_kialo_url(kialo_url)

        # Use the categorize_bill function to get the category names
        categories = categorize_bill(bill_details['description']) 
        webflow_category_ids = [map_category_to_id(cat) for cat in categories if map_category_to_id(cat) is not None]

        if not bill_url.startswith("http://") and not bill_url.startswith("https://"):
            logger.error(f"Invalid gov-url: {bill_url}")
            return None

        logger.info(f"slug: {slug}, title: {title}, kialo_url: {kialo_url}, description: {bill_details['description']}, gov-url: {bill_url}, category: {webflow_category_ids}")

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
                "category": webflow_category_ids,  # Add the category IDs
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
