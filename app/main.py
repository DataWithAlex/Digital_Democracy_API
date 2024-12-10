import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import boto3
import openai
from .bill_processing import fetch_bill_details, fetch_federal_bill_details, create_summary_pdf, create_summary_pdf_spanish, create_federal_summary_pdf, create_federal_summary_pdf_spanish, validate_and_generate_pros_cons
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest
from .webflow import WebflowAPI, generate_slug
from fastapi.responses import JSONResponse
import asyncio

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# AWS Credentials
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION")

logger.info("AWS credentials configuration")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

BUCKET_NAME = "ddp-bills-2"

# Database connection details
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_port = os.getenv('DB_PORT')

# SQLAlchemy engine and session maker
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize WebflowAPI
webflow_api = WebflowAPI(
    api_key=os.getenv("WEBFLOW_KEY"),
    collection_id="655288ef928edb1283067256",
    site_id=os.getenv("WEBFLOW_SITE_ID")
)

# Dependency: Database connection
def get_db():
    logger.info("Establishing database connection")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.info("Closing database connection")
        db.close()

@app.post("/update-bill/")
async def update_bill(request: FormRequest, db: Session = Depends(get_db)):
    history_value = f"{request.year}{request.bill_number}"
    logger.info(f"Starting update-bill() for bill: {history_value}")

    try:
        # Check if the history value exists
        existing_bill = db.query(Bill).filter(Bill.history == history_value).first()
        if existing_bill:
            logger.info(f"Bill with history {history_value} already exists. Process not run.")
            # ... rest of existing bill handling code ...

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
            try:
                # Set a timeout for the selenium script
                kialo_url = await asyncio.wait_for(
                    run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons),
                    timeout=39.0
                )
                if kialo_url is None:
                    logger.warning("Selenium script returned None, but continuing with processing")
            except asyncio.TimeoutError:
                logger.info("Selenium script timeout - continuing in background")
                return JSONResponse(
                    content={
                        "message": "Request received and processing in background. Please check back later.",
                        "status": "processing"
                    },
                    status_code=202
                )

            # ... rest of the code ...

    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return JSONResponse(content={"message": "Bill processed successfully"}, status_code=200)

# ... rest of the code ...