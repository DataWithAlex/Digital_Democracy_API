import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Response, Depends, BackgroundTasks
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import boto3
import openai
from .bill_processing import fetch_bill_details, fetch_federal_bill_details, create_summary_pdf, create_summary_pdf_spanish, create_federal_summary_pdf, create_federal_summary_pdf_spanish, validate_and_generate_pros_cons
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest, ProcessingStatus
from .webflow import WebflowAPI, generate_slug
from .logger_config import main_logger, get_bill_logger, selenium_logger, webflow_logger
from .middleware import RequestLoggingMiddleware
from fastapi.responses import JSONResponse
import datetime
import asyncio

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Log application startup
main_logger.info("Starting FastAPI application", extra={
    'environment': os.getenv('ENVIRONMENT', 'development'),
    'openai_api_configured': bool(openai.api_key),
})

def mask_sensitive_data(data):
    if not data:
        return data
    return f"{data[:4]}...{data[-4:]}" if len(data) > 8 else "****"

# AWS Credentials logging
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION")

main_logger.info("AWS credentials configuration", extra={
    'aws_region': aws_region,
    'aws_configured': bool(aws_access_key_id and aws_secret_access_key),
    'aws_key_length': len(aws_access_key_id) if aws_access_key_id else 0
})

# Database configuration logging
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_port = os.getenv('DB_PORT')

main_logger.info("Database configuration loaded", extra={
    'db_host': '[MASKED]',
    'db_name': db_name,
    'db_user': '[MASKED]',
    'db_port': db_port
})

# Webflow configuration logging
webflow_logger.info("Webflow configuration loaded", extra={
    'webflow_key_configured': bool(os.getenv('WEBFLOW_KEY')),
    'collection_key': '[MASKED]',
    'site_id': '[MASKED]'
})

# FastAPI app initialization
app = FastAPI()

# Initialize S3 client with masked logging
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

BUCKET_NAME = "ddp-bills-2"

# Dependency: Database connection
def get_db():
    main_logger.info("Establishing database connection")
    db = SessionLocal()
    try:
        yield db
    finally:
        main_logger.info("Closing database connection")
        db.close()

# Database connection details
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_port = os.getenv('DB_PORT')

main_logger.info(f"DB_HOST: {db_host}")
main_logger.info(f"DB_NAME: {db_name}")
main_logger.info(f"DB_USER: {mask_sensitive_data(db_user)}")
main_logger.info(f"DB_PASSWORD: {mask_sensitive_data(db_password)}")
main_logger.info(f"DB_PORT: {db_port}")

# SQLAlchemy engine and session maker
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize WebflowAPI with masked logging
webflow_api = WebflowAPI(
    api_key=os.getenv("WEBFLOW_KEY"),
    collection_id="655288ef928edb1283067256",
    site_id=os.getenv("WEBFLOW_SITE_ID")
)

main_logger.info(f"WEBFLOW_KEY: {mask_sensitive_data(os.getenv('WEBFLOW_KEY'))}")
main_logger.info(f"WEBFLOW_COLLECTION_KEY: 655288ef928edb1283067256")
main_logger.info(f"WEBFLOW_SITE_ID: {os.getenv('WEBFLOW_SITE_ID')}")

# Function to set up logging for each submission
def setup_individual_logging(submission_id):
    log_dir = os.path.join(BASE_LOGS_DIR, "submissions")
    os.makedirs(log_dir, exist_ok=True)
    
    submission_logger = get_bill_logger(submission_id)
    return submission_logger

@app.post("/upload-file/")
async def upload_file():
    file_path = 'test.txt'
    try:
        response = s3_client.upload_file(Filename=file_path, Bucket=BUCKET_NAME, Key='test.txt')
        return {"message": "File uploaded successfully", "response": str(response)}
    except Exception as e:
        main_logger.error(f"Failed to upload file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-file/")
async def delete_file():
    try:
        response = s3_client.delete_object(Bucket=BUCKET_NAME, Key='test.txt')
        return {"message": "File deleted successfully", "response": str(response)}
    except Exception as e:
        main_logger.error(f"Failed to delete file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def process_bill_background(request: FormRequest, db: Session, submission_id: str):
    bill_logger = get_bill_logger(submission_id)
    try:
        # Update status to processing
        status = ProcessingStatus(
            submission_id=submission_id,
            status="processing",
            message="Bill processing started",
            created_at=datetime.datetime.now()
        )
        db.add(status)
        db.commit()

        # Fetch bill details and process
        bill_details = fetch_federal_bill_details(request.session, request.bill_number, request.bill_type)
        bill_logger.info(f"Fetched bill details: {bill_details}")

        validate_bill_details(bill_details)
        slug = generate_slug(bill_details['title'])
        
        # Update status
        status.message = "Generating bill summary"
        db.commit()

        # Generate summary
        pdf_path, summary, pros, cons = generate_bill_summary(bill_details['full_text'], request.lan, bill_details['title'])
        bill_details['description'] = summary

        # Create new bill
        new_bill = add_new_bill(db, bill_details, summary, pros, cons, request.lan)
        
        # Update status to indicate long-running process
        status.message = "Bill details processed. Starting Kialo automation (this may take several minutes)"
        db.commit()

        # Run selenium script without timeout
        try:
            kialo_url = await run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
            if kialo_url:
                status.message = "Kialo automation completed successfully"
            else:
                status.message = "Kialo automation in progress (may take several minutes to complete)"
            db.commit()
        except Exception as e:
            bill_logger.error(f"Error in Selenium script: {str(e)}")
            status.message = "Kialo automation encountered an error, but continuing with processing"
            kialo_url = None
            db.commit()

        # Update status
        status.message = "Creating Webflow item"
        db.commit()

        # Create Webflow item
        result = create_webflow_item(bill_details, kialo_url, request, slug)
        if result:
            update_bill_with_webflow_info(new_bill, result, db)
            
            # Save form data
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

            # Update final status
            status.status = "completed"
            status.message = "Bill processing completed. Note: Kialo discussion may still be in progress."
            db.commit()
        else:
            status.status = "failed"
            status.message = "Failed to create Webflow item"
            db.commit()

    except Exception as e:
        bill_logger.error(f"Background processing failed: {str(e)}", exc_info=True)
        status.status = "failed"
        status.message = f"Processing failed: {str(e)}"
        db.commit()

@app.post("/process-federal-bill/")
async def process_federal_bill(request: FormRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    submission_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    bill_logger = setup_individual_logging(submission_id)
    
    bill_logger.info(f"Received request to generate federal bill summary for session: {request.session}, bill: {request.bill_number}, type: {request.bill_type}")
    
    try:
        # Create initial status entry
        status = ProcessingStatus(
            submission_id=submission_id,
            status="processing",
            message="Request received. Bill processing will continue in the background.",
            created_at=datetime.datetime.now()
        )
        db.add(status)
        db.commit()

        # Start background processing
        background_tasks.add_task(process_bill_background, request, db, submission_id)

        # Return immediate response with submission ID and clear explanation
        return JSONResponse(
            content={
                "message": "Request accepted. The bill processing has started and will continue in the background.",
                "note": "The Kialo automation may take several minutes to complete. You can check the status using the status endpoint.",
                "submission_id": submission_id,
                "status": "processing",
                "status_check_endpoint": f"/bill-status/{submission_id}"
            },
            status_code=202
        )

    except Exception as e:
        bill_logger.error(f"Failed to queue request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bill-status/{submission_id}")
async def get_bill_status(submission_id: str, db: Session = Depends(get_db)):
    status = db.query(ProcessingStatus).filter(ProcessingStatus.submission_id == submission_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    
    return {
        "submission_id": submission_id,
        "status": status.status,
        "message": status.message,
        "created_at": status.created_at,
        "updated_at": status.updated_at
    }

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

            # The response structure has changed - fieldData is now directly in the root
            webflow_item_data = webflow_item.get('fieldData', {})
            if not webflow_item_data:
                logger.error(f"Unexpected Webflow response structure: {webflow_item}")
                raise HTTPException(status_code=500, detail="Unexpected Webflow response structure")

            name = webflow_item_data.get('name')
            slug = webflow_item_data.get('slug')
            support_text = webflow_item_data.get('support', '') or ''
            oppose_text = webflow_item_data.get('oppose', '') or ''
            description = webflow_item_data.get('description', '')

            if not name or not slug:
                raise HTTPException(status_code=500, detail="Required fields 'name' or 'slug' are missing in the Webflow item.")

            # Initialize support_text and oppose_text if None
            if request.support == 'Support':
                support_text += f"\n{request.member_organization}"
            else:
                oppose_text += f"\n{request.member_organization}"

            # Prepare the data with the description field included
            data = {
                "fieldData": {
                    "support": support_text.strip(),
                    "oppose": oppose_text.strip(),
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "public": webflow_item_data.get("public", True),
                    "featured": webflow_item_data.get("featured", True)
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
            # Properly await the async selenium script
            kialo_url = await run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)

            logger.info("Creating Webflow item")
            result = webflow_api.create_live_collection_item(
                bill_url,
                {
                    **bill_details,
                    "description": summary
                },
                kialo_url,
                support_text=request.member_organization if request.support == "Support" else '',
                oppose_text=request.member_organization if request.support == "Oppose" else '',
                jurisdiction="FL"
            )

            if result is None:
                logger.error("Failed to create Webflow item")
                raise HTTPException(status_code=500, detail="Failed to create Webflow item")

            webflow_item_id, slug = result
            webflow_url = f"https://digitaldemocracyproject.org/bills/{slug}"

            new_bill.webflow_link = webflow_url
            new_bill.webflow_item_id = webflow_item_id
            db.commit()

            save_form_data(
                name=request.name,
                email=request.email,
                member_organization=request.member_organization,
                year=request.year,
                legislation_type="Florida Bills",
                session="N/A",
                bill_number=request.bill_number,
                bill_type=bill_details['govId'].split(" ")[0],
                support=request.support,
                govId=bill_details["govId"],
                db=db
            )

        if existing_bill:
            save_form_data(
                name=request.name,
                email=request.email,
                member_organization=request.member_organization,
                year=request.year,
                legislation_type="Florida Bills",
                session="N/A",
                bill_number=request.bill_number,
                bill_type=existing_bill.govId.split(" ")[0],
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
        logger.info("Database connection closed")

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
    """Global exception handler with enhanced logging"""
    error_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    main_logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            'error_id': error_id,
            'url': str(request.url),
            'method': request.method,
            'client_host': request.client.host if request.client else None,
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": str(exc) if os.getenv('ENVIRONMENT') == 'development' else "An unexpected error occurred"
        }
    )

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
            main_logger.info(f"Bill with slug '{slug}' exists in Webflow. Proceeding to update.")

            webflow_item = webflow_api.get_collection_item(webflow_item_id)

            if not webflow_item:
                main_logger.error(f"Failed to fetch Webflow item with ID: {webflow_item_id}")
                raise HTTPException(status_code=500, detail="Failed to fetch Webflow item.")

            fields = webflow_item['items'][0]

            existing_bill.title = fields.get('name', existing_bill.title)
            existing_bill.description = fields.get('description', existing_bill.description)
            existing_bill.slug = fields.get('slug', existing_bill.slug)
            existing_bill.kialo_url = fields.get('kialo-url', existing_bill.kialo_url)
            existing_bill.gov_url = fields.get('gov-url', existing_bill.gov_url)

            main_logger.info(f"Updated bill {existing_bill.id} with Webflow data and request inputs")
            db.commit()

        else:
            main_logger.info(f"Slug '{slug}' does not exist in Webflow. Creating new CMS item.")

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
                main_logger.error("Failed to create new Webflow CMS item")
                raise HTTPException(status_code=500, detail="Failed to create Webflow CMS item")

            webflow_item_id, new_slug = result
            webflow_url = f"https://digitaldemocracyproject.org/bills/{new_slug}"

            existing_bill.webflow_item_id = webflow_item_id
            existing_bill.webflow_link = webflow_url
            db.commit()

    except Exception as e:
        main_logger.error(f"An error occurred while updating the bill ID: {existing_bill.id}. Error: {str(e)}", exc_info=True)

    finally:
        db.close()
        main_logger.info(f"Database connection closed for bill ID: {existing_bill.id}")