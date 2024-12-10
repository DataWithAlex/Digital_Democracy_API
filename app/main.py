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
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest
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
            return JSONResponse(content={"message": "Bill already exists"}, status_code=200)

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
        kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
        if kialo_url is None:
            logger.warning("Selenium script failed but continuing with processing")

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

        # Save form data
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

    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
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