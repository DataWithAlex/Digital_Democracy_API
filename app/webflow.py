import requests
import logging
import json
import re
from typing import Dict, Optional
from .logger_config import webflow_logger

# Logging configuration
logging.basicConfig(level=logging.INFO)

def generate_slug(title):
    """Generate a URL-friendly slug from a title"""
    try:
        webflow_logger.debug(f"Generating slug for title", extra={'title': title})
        # Convert to lowercase
        slug = title.lower()
        # Replace spaces with hyphens
        slug = slug.replace(" ", "-")
        # Remove invalid characters
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        webflow_logger.debug(f"Generated slug", extra={'slug': slug})
        return slug
    except Exception as e:
        webflow_logger.error(f"Error generating slug: {str(e)}", 
                           extra={'title': title}, exc_info=True)
        raise

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

def clean_kialo_url(url):
    """Clean and format the Kialo URL."""
    if url is None:
        return None
        
    # If it's a coroutine (async result), return as is - will be cleaned later
    if hasattr(url, '__await__'):
        return url
        
    try:
        parts = url.split("&action=")
        return parts[0] if parts else url
    except (AttributeError, IndexError):
        return url

class WebflowAPI:
    def __init__(self, api_key: str, collection_id: str, site_id: str):
        self.api_key = api_key
        self.collection_id = collection_id
        self.site_id = site_id
        self.member_org_collection_id = "65bd4aca31deb7e14e53d5dc"  # Member Organizations collection ID
        webflow_logger.info("Initializing WebflowAPI", extra={
            'collection_id': collection_id,
            'site_id': site_id
        })
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'accept-version': '2.0.0',  # Use V2 API version
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        self.base_url = "https://api.webflow.com/v2"

        # Add a mapping for the jurisdictions
        self.jurisdiction_map = {
            'US': '65810f6b889af86635a71b49',  # Replace with the correct ItemRef for US
            'FL': '655288ef928edb128306745f',  # Replace with the correct ItemRef for FL
        }

    def fetch_all_cms_items(self):
        """Fetch all CMS items from the Webflow collection (V2 API)."""
        items_endpoint = f"{self.base_url}/collections/{self.collection_id}/items"
        response = requests.get(items_endpoint, headers=self.headers)

        webflow_logger.info(f"Fetching CMS items from: {items_endpoint}")

        if response.status_code == 200:
            items_data = response.json().get('items', [])
            webflow_logger.info(f"Successfully fetched {len(items_data)} CMS items from Webflow.")
            return items_data
        else:
            webflow_logger.error(f"Failed to fetch CMS items: {response.status_code} - {response.text}")
            return []

    def check_slug_exists(self, slug, items_data):
        """Check if the generated slug already exists in the fetched CMS items (V2 API)."""
        for item in items_data:
            if item['fieldData']['slug'] == slug:  # Adjusted for V2 API response structure
                webflow_logger.info(f"Slug '{slug}' already exists with ID: {item['id']}")
                return True
        return False

    def search_member_organization(self, org_name: str) -> Optional[str]:
        """Search for a member organization by name and return its ID if found."""
        webflow_logger.info(f"Searching for member organization: {org_name}")
        
        # Fetch all items from member organizations collection
        items_endpoint = f"{self.base_url}/collections/{self.member_org_collection_id}/items"
        response = requests.get(items_endpoint, headers=self.headers)
        
        if response.status_code != 200:
            webflow_logger.error(f"Failed to fetch member organizations: {response.status_code} - {response.text}")
            return None
            
        items = response.json().get('items', [])
        webflow_logger.info(f"Retrieved {len(items)} member organizations")
        
        # Log all retrieved organizations
        org_list = [{"name": item['fieldData'].get('name'), "id": item['id']} for item in items]
        webflow_logger.info(f"Retrieved member organizations: {json.dumps(org_list, indent=2)}")
        
        # Search for exact match first, then case-insensitive match
        for item in items:
            if item['fieldData'].get('name') == org_name:
                webflow_logger.info(f"Found exact match for organization: {org_name} (ID: {item['id']})")
                return item['id']
                
        for item in items:
            if item['fieldData'].get('name').lower() == org_name.lower():
                webflow_logger.info(f"Found case-insensitive match for organization: {org_name} (ID: {item['id']})")
                return item['id']
                
        webflow_logger.info(f"No matching organization found for: {org_name}")
        return None

    def create_member_organization(self, org_name: str) -> Optional[str]:
        """Create a new member organization and return its ID."""
        webflow_logger.info(f"Creating new member organization: {org_name}")
        
        # Generate slug from organization name
        slug = generate_slug(org_name)
        
        # Prepare the data payload
        data = {
            "fieldData": {
                "name": org_name,
                "slug": slug
            }
        }
        
        webflow_logger.info(f"Creating member organization with data: {json.dumps(data, indent=2)}")
        
        # Create new organization
        create_endpoint = f"{self.base_url}/collections/{self.member_org_collection_id}/items/live"
        response = requests.post(create_endpoint, headers=self.headers, json=data)
        
        if response.status_code not in [200, 201, 202]:
            webflow_logger.error(f"Failed to create member organization: {response.status_code} - {response.text}")
            return None
            
        try:
            response_data = response.json()
            org_id = response_data['id']
            webflow_logger.info(f"Successfully created member organization: {org_name} (ID: {org_id})")
            return org_id
        except Exception as e:
            webflow_logger.error(f"Error parsing create organization response: {str(e)}", exc_info=True)
            return None

    def handle_member_organization(self, org_name: str) -> Optional[str]:
        """Search for existing organization or create new one if not found."""
        if not org_name:
            webflow_logger.warning("No organization name provided")
            return None
            
        # Search for existing organization
        org_id = self.search_member_organization(org_name)
        
        if org_id:
            return org_id
            
        # Create new organization if not found
        return self.create_member_organization(org_name)

    def create_live_collection_item(self, bill_url, bill_details: Dict, kialo_url: str, support_text: str, oppose_text: str, jurisdiction: str, member_organization: Optional[str] = None) -> Optional[tuple]:
        slug = generate_slug(bill_details['title'])
        title = reformat_title(bill_details['title'])
        kialo_url = clean_kialo_url(kialo_url)

        if not bill_url.startswith("http://") and not bill_url.startswith("https://"):
            webflow_logger.error(f"Invalid gov-url: {bill_url}")
            return None

        # Map jurisdiction to its corresponding ItemRef
        jurisdiction_item_ref = self.jurisdiction_map.get(jurisdiction)
        if not jurisdiction_item_ref:
            webflow_logger.error(f"Invalid jurisdiction: {jurisdiction}")
            return None

        webflow_logger.info(f"slug: {slug}, title: {title}, kialo_url: {kialo_url}, description: {bill_details['description']}, gov-url: {bill_url}")

        # Prepare the data payload
        data = {
            "fieldData": {
                "name": title,
                "slug": slug,
                "post-body": "",
                "jurisdiction": jurisdiction_item_ref,
                "voatzid": "",
                "kialo-url": kialo_url,
                "gov-url": bill_url,
                "bill-score": 0.0,
                "description": bill_details['description'],
                "support": support_text,
                "oppose": oppose_text,
                "public": True,
                "featured": True
            }
        }

        # Add categories if they exist
        if 'categories' in bill_details and bill_details['categories']:
            data['fieldData']['category'] = bill_details['categories']
            webflow_logger.info(f"Adding categories to item: {bill_details['categories']}")

        # Add member organization if provided
        if member_organization:
            org_id = self.handle_member_organization(member_organization)
            if org_id:
                data['fieldData']['member-organizations'] = [org_id]
                webflow_logger.info(f"Adding member organization to item: {org_id}")

        webflow_logger.info(f"JSON Payload: {json.dumps(data, indent=4)}")

        # Updated endpoint for V2 API
        create_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/live"
        response = requests.post(create_item_endpoint, headers=self.headers, json=data)
        webflow_logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201, 202]:
            try:
                response_data = response.json()
                item_id = response_data.get('id')
                slug = response_data['fieldData'].get('slug')
                webflow_logger.info(f"Live collection item created successfully, ID: {item_id}, slug: {slug}")
                return item_id, slug
            except Exception as e:
                webflow_logger.error(f"Error parsing Webflow API response: {str(e)}", exc_info=True)
                return None
        else:
            webflow_logger.error(f"Failed to create live collection item: {response.status_code} - {response.text}")
            return None

    def update_collection_item(self, item_id: str, data: Dict) -> bool:
        update_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}/live"

        # Debugging: Print the JSON payload with sensitive data masked
        debug_data = data.copy()
        if 'fieldData' in debug_data:
            if 'support' in debug_data['fieldData']:
                debug_data['fieldData']['support'] = '[MASKED]'
            if 'oppose' in debug_data['fieldData']:
                debug_data['fieldData']['oppose'] = '[MASKED]'
        webflow_logger.info(f"JSON Payload: {json.dumps(debug_data, indent=4)}")

        # Making the PATCH request to update the collection item (V2 API uses PATCH)
        response = requests.patch(update_item_endpoint, headers=self.headers, json=data)
        webflow_logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code not in [200, 201]:
            webflow_logger.error(f"Failed to update collection item: {response.status_code} - {response.text}")
            return False

        return True

    def get_collection_item(self, item_id: str) -> Optional[Dict]:
        get_item_endpoint = f"{self.base_url}/collections/{self.collection_id}/items/{item_id}"

        response = requests.get(get_item_endpoint, headers=self.headers)
        webflow_logger.info(f"Webflow API Response Status: {response.status_code}, Response Text: {response.text}")

        if response.status_code in [200, 201]:
            return response.json()
        else:
            webflow_logger.error(f"Failed to get collection item: {response.status_code} - {response.text}")
            return None