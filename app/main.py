import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import boto3
import openai
from .bill_processing import fetch_bill_details, fetch_federal_bill_details, create_summary_pdf, create_summary_pdf_spanish, create_federal_summary_pdf, create_federal_summary_pdf_spanish, validate_and_generate_pros_cons, setup_bill_logging
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest  # Ensure FormRequest is imported
from .webflow import WebflowAPI, generate_slug
from .logger_config import logger
from fastapi.responses import JSONResponse
import datetime

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# Check and log AWS credentials
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION")

logger.info(f"AWS_ACCESS_KEY_ID: {aws_access_key_id}")
logger.info(f"AWS_SECRET_ACCESS_KEY: {aws_secret_access_key}")
logger.info(f"AWS_DEFAULT_REGION: {aws_region}")

if not all([aws_access_key_id, aws_secret_access_key, aws_region]):
    logger.error("AWS credentials are not set correctly.")
else:
    logger.info("AWS credentials are set correctly.")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

BUCKET_NAME = "ddp-bills-2"  # Confirm this is the correct bucket name

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Dependency: Database connection
def get_db():
    logger.info("Establishing database connection")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.info("Closing database connection")
        db.close()

# Database connection details
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_port = os.getenv('DB_PORT')

logger.info(f"DB_HOST: {db_host}")
logger.info(f"DB_NAME: {db_name}")
logger.info(f"DB_USER: {db_user}")
logger.info(f"DB_PASSWORD: {db_password}")
logger.info(f"DB_PORT: {db_port}")

# SQLAlchemy engine and session maker
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize WebflowAPI
webflow_api = WebflowAPI(
    api_key=os.getenv("WEBFLOW_KEY"),
    collection_id="655288ef928edb1283067256",  # Updated with the actual collection ID
    site_id=os.getenv("WEBFLOW_SITE_ID")
)

logger.info(f"WEBFLOW_KEY: {os.getenv('WEBFLOW_KEY')}")
logger.info(f"WEBFLOW_COLLECTION_KEY: 655288ef928edb1283067256")  # Updated with the actual collection ID
logger.info(f"WEBFLOW_SITE_ID: {os.getenv('WEBFLOW_SITE_ID')}")

@app.post("/upload-file/")
async def upload_file():
    file_path = 'test.txt'  # Confirm the file path is correct and accessible
    try:
        response = s3_client.upload_file(Filename=file_path, Bucket=BUCKET_NAME, Key='test.txt')
        return {"message": "File uploaded successfully", "response": str(response)}
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-file/")
async def delete_file():
    try:
        response = s3_client.delete_object(Bucket=BUCKET_NAME, Key='test.txt')
        return {"message": "File deleted successfully", "response": str(response)}
    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize WebflowAPI for V2
webflow_api = WebflowAPI(
    api_key=os.getenv("WEBFLOW_KEY"),
    collection_id="655288ef928edb1283067256",  # Update with your actual collection ID
    site_id=os.getenv("WEBFLOW_SITE_ID")
)

@app.post("/process-federal-bill/", response_class=Response)
async def process_federal_bill(request: FormRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate federal bill summary for session: {request.session}, bill: {request.bill_number}, type: {request.bill_type}")
    try:
        bill_details = fetch_federal_bill_details(request.session, request.bill_number, request.bill_type)
        logger.info(f"Fetched bill details: {bill_details}")

        validate_bill_details(bill_details)

        # Set up logging for this specific bill
        bill_logger = setup_bill_logging(bill_details["title"])

        # Use the bill-specific logger
        bill_logger.info("Processing federal bill")

        # Additional processing logic here...

    except Exception as e:
        logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return JSONResponse(content={"message": "Bill processed successfully"}, status_code=200)

def save_form_data(name, email, member_organization, year, legislation_type, session, bill_number, bill_type, support, govId, db: Session):
    form_data = FormData(
        name=name,
        email=email,
        member_organization=member_organization,
        year=year,
        legislation_type=legislation_type,
        session=session,
        bill_number=bill_number,
        bill_type=bill_type,
        support=support,
        govId=govId,
        created_at=datetime.datetime.now()
    )
    db.add(form_data)
    db.commit()

# Exception handlers
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return JSONResponse(content={"message": "An internal server error occurred."})

def add_new_bill(db, bill_details, summary, pros, cons, language):
    new_bill = Bill(
        govId=bill_details["govId"],
        billTextPath=bill_details["billTextPath"],
        history=bill_details["history"]
    )
    db.add(new_bill)
    db.commit()

    for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
        new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language=language.upper())
        db.add(new_meta)
    db.commit()

    return new_bill

def create_webflow_item(bill_details, kialo_url, request, slug):
    return webflow_api.create_live_collection_item(
        bill_details['gov-url'],
        bill_details,
        kialo_url,
        support_text=request.member_organization if request.support == "Support" else '',
        oppose_text=request.member_organization if request.support == "Oppose" else '',
        jurisdiction="US" if 'US' in bill_details['govId'] else 'FL'
    )

def update_bill_with_webflow_info(new_bill, result, db):
    webflow_item_id, slug = result
    webflow_url = f"https://digitaldemocracyproject.org/bills/{slug}"
    new_bill.webflow_link = webflow_url
    new_bill.webflow_item_id = webflow_item_id
    db.commit()

def update_existing_bill(existing_bill, request, db):
    try:
        cms_items = webflow_api.fetch_all_cms_items()

        slug = existing_bill.slug
        slug_exists, webflow_item_id = webflow_api.check_slug_exists(slug, cms_items)

        if slug_exists:
            logger.info(f"Bill with slug '{slug}' exists in Webflow. Proceeding to update.")

            webflow_item = webflow_api.get_collection_item(webflow_item_id)

            if not webflow_item:
                logger.error(f"Failed to fetch Webflow item with ID: {webflow_item_id}")
                raise HTTPException(status_code=500, detail="Failed to fetch Webflow item.")

            fields = webflow_item['items'][0]

            existing_bill.title = fields.get('name', existing_bill.title)
            existing_bill.description = fields.get('description', existing_bill.description)
            existing_bill.slug = fields.get('slug', existing_bill.slug)
            existing_bill.kialo_url = fields.get('kialo-url', existing_bill.kialo_url)
            existing_bill.gov_url = fields.get('gov-url', existing_bill.gov_url)

            logger.info(f"Updated bill {existing_bill.id} with Webflow data and request inputs")
            db.commit()

        else:
            logger.info(f"Slug '{slug}' does not exist in Webflow. Creating new CMS item.")

            result = webflow_api.create_live_collection_item(
                existing_bill.gov_url,
                {
                    'name': existing_bill.title,
                    'slug': slug,
                    'description': existing_bill.description
                },
                existing_bill.kialo_url,
                support_text=request.member_organization if request.support == "Support" else '',
                oppose_text=request.member_organization if request.support == "Oppose" else '',
                jurisdiction="US" if 'US' in existing_bill.govId else 'FL'
            )

            if result is None:
                logger.error("Failed to create new Webflow CMS item")
                raise HTTPException(status_code=500, detail="Failed to create Webflow CMS item")

            webflow_item_id, new_slug = result
            webflow_url = f"https://digitaldemocracyproject.org/bills/{new_slug}"

            existing_bill.webflow_item_id = webflow_item_id
            existing_bill.webflow_link = webflow_url
            db.commit()

    except Exception as e:
        logger.error(f"An error occurred while updating the bill ID: {existing_bill.id}. Error: {str(e)}", exc_info=True)

    finally:
        db.close()
        logger.info(f"Database connection closed for bill ID: {existing_bill.id}")