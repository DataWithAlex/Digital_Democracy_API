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
    """
    Reformat the title to include the bill type and number in parentheses.
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
    
    # Extract the bill type and number (e.g., "HR 9056") including prefix
    bill_type_number = " ".join(bill_identifier.split()[1:3])  # Takes only the second and third parts, which are the type and number
    
    # Append prefix to bill number
    prefix = bill_identifier.split()[0]  # Extracts "SB", "HR", etc.
    formatted_bill_number = f"{prefix} {bill_type_number}"

    # Format the new title as "Description (Bill Type Number)"
    new_title = f"{description} ({formatted_bill_number})"
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
        
        # Add a mapping for the jurisdictions
        self.jurisdiction_map = {
            'FL': '655288ef928edb128306745f',  # Replace with the actual ItemRef for FL
            'US': '65810f6b889af86635a71b49'  # Replace with the actual ItemRef for US
        }

    def create_webflow_payload(self, bill_details, kialo_url, support_text, oppose_text, jurisdiction):
        """
        Creates the payload for Webflow API.

        Args:
            bill_details (dict): A dictionary containing details about the bill.
            kialo_url (str): The URL to the discussion on Kialo.
            support_text (str): The support text for the bill.
            oppose_text (str): The oppose text for the bill.
            jurisdiction (str): The jurisdiction identifier.

        Returns:
            dict: A dictionary formatted as the payload for the Webflow API.
        """
        try:
            # Generate slug from the title
            slug = generate_slug(bill_details['title'])
            title = reformat_title(bill_details['title'])
            
            # Validate jurisdiction mapping
            jurisdiction_item_ref = self.jurisdiction_map.get(jurisdiction)
            if not jurisdiction_item_ref:
                logging.error(f"Invalid jurisdiction: {jurisdiction}")
                return None

            # Format the payload data
            payload = {
                "isArchived": False,
                "isDraft": False,
                "fieldData": {
                    "name": title,
                    "slug": slug,
                    "post-body": "",
                    "jurisdiction": jurisdiction_item_ref,
                    "voatzid": "",
                    "kialo-url": kialo_url,
                    "gov-url": bill_details['gov-url'],
                    "bill-score": 0.0,
                    "description": bill_details.get('description', ''),
                    "support": support_text,
                    "oppose": oppose_text,
                    "public": True,
                    "featured": True,
                    "category": bill_details["categories"]
                }
            }
            
            logging.info(f"Webflow Payload Created: {json.dumps(payload, indent=4)}")
            return payload
        
        except Exception as e:
            logging.error(f"Failed to create Webflow payload: {e}")
            return None

    def create_live_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str, jurisdiction: str) -> Optional[str]:
        try:
            slug = generate_slug(bill_details['title'])
            title = reformat_title(bill_details['title'])
            kialo_url = clean_kialo_url(kialo_url)

            # Ensure categories are formatted correctly
            if not isinstance(bill_details['categories'], list):
                logger.error("Categories field is not a list.")
                return None

            data = self.create_webflow_payload(bill_details, kialo_url, support_text, oppose_text, jurisdiction)
            if not data:
                logger.error("Failed to create Webflow payload.")
                return None

            # Send request to Webflow API
            response = requests.post(f"{self.base_url}/v2/collections/{self.collection_id}/items/live", headers=self.headers, json=data)
            if response.status_code in [200, 201]:
                item_id = response.json().get('id')
                slug = data['fieldData']['slug']
                logger.info(f"Created Webflow item: ID={item_id}, Slug={slug}")
                return item_id, slug
            else:
                logger.error(f"Failed to create Webflow item: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception in create_live_collection_item: {e}", exc_info=True)
            return None

    # ... Other methods remain unchanged ...

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
