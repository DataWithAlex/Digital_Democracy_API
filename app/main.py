import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import boto3
import openai
from .bill_processing import fetch_bill_details, fetch_federal_bill_details, create_summary_pdf, create_summary_pdf_spanish, create_federal_summary_pdf, create_federal_summary_pdf_spanish, validate_and_generate_pros_cons
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest  # Ensure FormRequest is imported
from .webflow import WebflowAPI, get_top_categories, format_categories_for_webflow, categories
from .logger_config import logger
from fastapi.responses import JSONResponse
import datetime
from .utils import get_category_ids  # Only import get_category_ids


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


# Function to process bill requests
# main.py

# Function to process bill requests
def process_bill_request(bill_request: BillRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate bill summary for URL: {bill_request.url}")
    try:
        bill_details = fetch_bill_details(bill_request.url)
        
        # Generate and format categories using GPT-4
        bill_text = bill_details.get("full_text", "")
        openai_categories = get_top_categories(bill_text, categories)
        formatted_categories = format_categories_for_webflow(openai_categories)
        
        logger.info(f"Formatted Categories for Webflow: {formatted_categories}")

        # Generate PDF and summaries based on language preference
        if bill_request.lan == "es":
            pdf_path, summary, pros, cons = create_summary_pdf_spanish(bill_details['pdf_path'], "output/bill_summary_spanish.pdf", bill_details['title'])
        else:
            pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])

        # Ensure the description field is updated with the summary
        bill_details['description'] = summary

        # Check if the bill already exists in the database
        existing_bill = db.query(Bill).filter(Bill.govId == bill_details["govId"]).first()
        if not existing_bill:
            new_bill = Bill(govId=bill_details["govId"], billTextPath=bill_details["billTextPath"])
            db.add(new_bill)
            db.commit()

            for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
                new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language=bill_request.lan.upper())
                db.add(new_meta)
            db.commit()

            logger.info("About to run Selenium script")
            kialo_url = run_selenium_script(
                title=bill_details['govId'],
                summary=summary,
                pros_text=pros,
                cons_text=cons
            )
            logger.info("Finished running Selenium script")
            logger.info(f"Kialo URL: {kialo_url}")

            logger.info("Creating Webflow item")
            webflow_item_id = webflow_api.create_live_collection_item(
                bill_request.url, 
                bill_details, 
                kialo_url, 
                support_text=bill_request.member_organization if bill_request.support == "Support" else '', 
                oppose_text=bill_request.member_organization if bill_request.support == "Oppose" else '', 
                jurisdiction="FL",  # Example jurisdiction for Florida bills
                formatted_categories=formatted_categories  # Pass the formatted categories here
            )
        else:
            logger.info(f"Bill with govId {bill_details['govId']} already exists. Skipping bill creation.")

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                return Response(content=pdf_file.read(), media_type="application/pdf")
        else:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTP exception occurred: {http_exc}", exc_info=True)
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/process-federal-bill/", response_class=Response)
async def process_federal_bill(request: FormRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate federal bill summary for session: {request.session}, bill: {request.bill_number}, type: {request.bill_type}")
    try:
        bill_details = fetch_federal_bill_details(request.session, request.bill_number, request.bill_type)
        logger.info(f"Fetched bill details: {bill_details}")

        validate_bill_details(bill_details)

        # Generate category IDs based on bill text
        category_names = bill_details.get("categories", [])  # Assume this key contains category names
        category_ids = get_category_ids(category_names)
        bill_details["categories"] = category_ids  # Update the bill details with category IDs

        pdf_path, summary, pros, cons = generate_bill_summary(bill_details['full_text'], request.lan, bill_details['title'])

        # Ensure the description field is updated with the summary
        bill_details['description'] = summary
        
        existing_bill = db.query(Bill).filter(Bill.govId == bill_details["govId"]).first()
        if not existing_bill:
            new_bill = add_new_bill(db, bill_details, summary, pros, cons, request.lan)
            kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
            result = create_webflow_item(bill_details, kialo_url, request)

            if result is None:
                logger.error("Failed to create Webflow item")
                raise HTTPException(status_code=500, detail="Failed to create Webflow item")

            update_bill_with_webflow_info(new_bill, result, db)
        else:
            update_existing_bill(existing_bill, request, db)

        save_form_data(
            name=request.name,
            email=request.email,
            member_organization=request.member_organization,
            year=request.year,
            legislation_type="Federal Bills",
            session=request.session,
            bill_number=request.bill_number,
            bill_type=request.bill_type,
            support=request.support,
            govId=bill_details["govId"],
            db=db
        )

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                return Response(content=pdf_file.read(), media_type="application/pdf")
        else:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTP exception occurred: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def validate_bill_details(bill_details):
    required_fields = ["govId", "billTextPath", "full_text", "history", "gov-url"]
    if not all(k in bill_details for k in required_fields):
        raise HTTPException(status_code=500, detail="Required bill details are missing.")

def generate_bill_summary(full_text, language, title):
    if language == "es":
        return create_federal_summary_pdf_spanish(full_text, "output/federal_bill_summary_spanish.pdf", title)
    else:
        return create_federal_summary_pdf(full_text, "output/federal_bill_summary.pdf", title)

@app.post("/update-bill/", response_class=Response)
async def update_bill(request: FormRequest, db: Session = Depends(get_db)):
    history_value = f"{request.year}{request.bill_number}"

    logger.info(f"Starting update-bill() for bill: {history_value}")

    try:
        # Check if the history value exists
        existing_bill = db.query(Bill).filter(Bill.history == history_value).first()
        if existing_bill:
            logger.info(f"Bill with history {history_value} already exists. Process not run.")

            # Get the Webflow item ID
            webflow_item_id = existing_bill.webflow_item_id
            if not webflow_item_id:
                raise HTTPException(status_code=500, detail="Webflow item ID is missing for the existing bill.")

            # Get the existing Webflow item
            webflow_item = webflow_api.get_collection_item(webflow_item_id)
            logger.info(f"Webflow API Response: {webflow_item}")
            if not webflow_item:
                raise HTTPException(status_code=500, detail="Failed to retrieve Webflow item.")

            # Ensure all required fields are present
            webflow_item_data = webflow_item.get('items', [])[0]
            name = webflow_item_data.get('name')
            slug = webflow_item_data.get('slug')
            support_text = webflow_item_data.get('support', '') or ''
            oppose_text = webflow_item_data.get('oppose', '') or ''
            description = webflow_item_data.get('description', '')  # Ensure description is retrieved

            if not name or not slug:
                raise HTTPException(status_code=500, detail="Required fields 'name' or 'slug' are missing in the Webflow item.")

            # Initialize support_text and oppose_text if None
            if request.support == 'Support':
                support_text += f"\n{request.member_organization}"
            else:
                oppose_text += f"\n{request.member_organization}"

            # Prepare the data with the description field included
            data = {
                "fields": {
                    "support": support_text.strip(),
                    "oppose": oppose_text.strip(),
                    "name": name,
                    "slug": slug,
                    "description": description,  # Ensure description is updated
                    "_draft": webflow_item_data.get("_draft", False),
                    "_archived": webflow_item_data.get("_archived", False)
                }
            }

            if not webflow_api.update_collection_item(webflow_item_id, data):
                raise HTTPException(status_code=500, detail="Failed to update Webflow item.")

        else:
            # New bill creation
            bill_url = f"https://www.flsenate.gov/Session/Bill/{request.year}/{request.bill_number}"
            bill_details = fetch_bill_details(bill_url)
            logger.info(f"Obtained bill details for: {bill_url}")

            if not all(k in bill_details for k in ["govId", "billTextPath", "pdf_path", "description"]):
                raise HTTPException(status_code=500, detail="Required bill details are missing.")

            # Generate category IDs based on bill text
            category_names = bill_details.get("categories", [])
            category_ids = get_category_ids(category_names)
            bill_details["categories"] = category_ids

            new_bill = Bill(
                govId=bill_details["govId"], 
                billTextPath=bill_details["billTextPath"], 
                history=history_value
            )
            db.add(new_bill)
            db.commit()

            pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
            logger.info("Generated Summary")

            for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
                new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language="EN")
                db.add(new_meta)
            db.commit()

            logger.info("Running Selenium script")
            kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)

            logger.info("Creating Webflow item")
            # Pass the description field and support/oppose text to Webflow API
            result = webflow_api.create_live_collection_item(
                bill_url,
                {
                    **bill_details,  # Ensure bill details include description
                    "description": summary  # Set description to the generated summary
                },
                kialo_url,
                support_text=request.member_organization if request.support == "Support" else '',
                oppose_text=request.member_organization if request.support == "Oppose" else '',
                jurisdiction="FL"  # Set jurisdiction to "FL" for Florida bills
            )

            if result is None:
                logger.error("Failed to create Webflow item")
                raise HTTPException(status_code=500, detail="Failed to create Webflow item")

            webflow_item_id, slug = result
            webflow_url = f"https://digitaldemocracyproject.org/bills/{slug}"

            new_bill.webflow_link = webflow_url
            new_bill.webflow_item_id = webflow_item_id  # Store the Webflow item ID
            db.commit()

            # Save form data to the database with new bill details
            save_form_data(
                name=request.name,
                email=request.email,
                member_organization=request.member_organization,
                year=request.year,
                legislation_type="Florida Bills",
                session="N/A",
                bill_number=request.bill_number,
                bill_type=bill_details['govId'].split(" ")[0],  # Assuming bill type is part of govId
                support=request.support,
                govId=bill_details["govId"],
                db=db
            )

        # Save form data to the database with existing bill details
        if existing_bill:
            save_form_data(
                name=request.name,
                email=request.email,
                member_organization=request.member_organization,
                year=request.year,
                legislation_type="Florida Bills",
                session="N/A",
                bill_number=request.bill_number,
                bill_type=existing_bill.govId.split(" ")[0],  # Assuming bill type is part of govId
                support=request.support,
                govId=existing_bill.govId,
                db=db
            )

    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
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

def create_webflow_item(bill_details, kialo_url, request):
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
    webflow_item_id = existing_bill.webflow_item_id
    webflow_item = webflow_api.get_collection_item(webflow_item_id)

    fields = webflow_item['items'][0]
    support_text = fields.get('support', '') or ''
    oppose_text = fields.get('oppose', '') or ''

    if request.support == "Support":
        support_text += f"\n{request.member_organization}"
    else:
        oppose_text += f"\n{request.member_organization}"

    data = {
        "fields": {
            "support": support_text.strip(),
            "oppose": oppose_text.strip(),
            "name": fields['name'],
            "slug": fields['slug'],
            "_draft": fields['_draft'],
            "_archived": fields['_archived']
        }
    }

    if not webflow_api.update_collection_item(webflow_item_id, data):
        logger.error("Failed to update Webflow item")
        raise HTTPException(status_code=500, detail="Failed to update Webflow item")