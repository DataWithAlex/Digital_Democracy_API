import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from .web_scraping import fetch_bill_details
from .pdf_generation import create_summary_pdf, create_summary_pdf_spanish
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta
import openai
from .webflow import WebflowAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from .logger_config import logger

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Depnoti

# Database connection details
#db_host = 'ddp-api.czqcac8oivov.us-east-1.rds.amazonaws.com'
#db_name = 'digital_democracy'
#db_user = 'DataWithAlex'
#db_password = '%Mineguy29'
#db_port = 3306

db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_port = os.getenv('DB_PORT')

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

DATABASE_URL = "mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{dp_port}/{db_name}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize WebflowAPI
webflow_api = WebflowAPI(
    api_key= os.getenv("WEBFLOW_KEY"),
    collection_id= os.getenv("WEBFLOW_COLLECTION_KEY"),
    site_id= os.getenv("WEBFLOW_SITE_ID")
)

logger.info(f"WEBFLOW_KEY {os.getenv('WEBFLOW_SITE_ID')} WEBFLOW_COLLECTION_KEY {os.getenv('WEBFLOW_COLLECTION_KEY')} WEBFLOW_SITE_ID {os.getenv('WEBFLOW_SITE_ID')}")

# Exception handlers
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return {"message": "An internal server error occurred."}

# Define logger
from .logger_config import logger

def process_bill_request(bill_request: BillRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate bill summary for URL: {bill_request.url}")
    try:
        # Fetch bill details
        logger.info(f"About to run fetch_bill_details() with url: {bill_request.url}")
        bill_details = fetch_bill_details(bill_request.url)

        # Log all the values in bill_details
        logger.info("Bill details:")
        for key, value in bill_details.items():
            logger.info(f"{key}: {value}")

        # Ensure required keys are in bill_details
        if not all(k in bill_details for k in ["govId", "billTextPath", "pdf_path"]):
            raise HTTPException(status_code=500, detail="Required bill details are missing.")

        # Check language and generate PDF accordingly
        if bill_request.lan == "es":
            pdf_path, summary, pros, cons = create_summary_pdf_spanish(bill_details['pdf_path'], "output/bill_summary_spanish.pdf", bill_details['title'])
        else:
            pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])

        # Insert bill details into the database
        new_bill = Bill(govId=bill_details["govId"], billTextPath=bill_details["billTextPath"])
        db.add(new_bill)
        db.commit()

        # Insert summary, pros, and cons into bill_meta
        for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
            new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language=bill_request.lan.upper())
            db.add(new_meta)
        db.commit()

        logger.info("About to run Selenium script")
        # Run the Selenium script after generating the summary
        kialo_url = run_selenium_script(
            title=bill_details['govId'],
            summary=summary,
            pros_text=pros,
            cons_text=cons
        )
        logger.info("Finished running Selenium script")
        logger.info(f"Kialo URL: {kialo_url}")

        # Update bill_details with summary for Webflow item creation
        bill_details['description'] = summary  # Update description with summary
        logger.info(f"Summary for Webflow: {summary}")

        logger.info("Creating Webflow item")
        # Now, create a Webflow CMS item with the returned details
        webflow_item_id = webflow_api.create_collection_item(bill_request.url, bill_details, kialo_url)
        #webflow_item_id = webflow_api.create_collection_item(bill_details, kialo_url, bill_url=bill_request.url)

        # Check if PDF was successfully created
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                return Response(content=pdf_file.read(), media_type="application/pdf")
        else:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")

    except HTTPException as http_exc:
        db.rollback()
        logging.error(f"HTTP exception occurred: {http_exc}", exc_info=True)
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

from fastapi.responses import JSONResponse  # Import JSONResponse

@app.post("/update-bill/", response_class=Response)
async def update_bill(year: str, bill_number: str, db: Session = Depends(get_db)):
    history_value = f"{year}{bill_number}"

    logger.info(f"Starting update-bill() for bill: {history_value}")

    # Check if the history value exists
    existing_bill = db.query(Bill).filter(Bill.history == history_value).first()
    if existing_bill:
        logger.info(f"Bill with history {history_value} already exists. Process not run.")
        return JSONResponse(content={"message": f"Bill with history {history_value} already exists. Process not run."}, status_code=200)

    bill_url = f"https://www.flsenate.gov/Session/Bill/{year}/{bill_number}"
    bill_details = fetch_bill_details(bill_url)
    logger.info(f"Obtained bill_details for: {bill_url}")

    if not all(k in bill_details for k in ["govId", "billTextPath", "pdf_path"]):
        raise HTTPException(status_code=500, detail="Required bill details are missing.")

    new_bill = Bill(govId=bill_details["govId"], billTextPath=bill_details["billTextPath"], history=history_value)
    db.add(new_bill)
    db.commit()

    pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
    logger.info("Generated Summary")

    for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
        new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language="EN")
        db.add(new_meta)
    db.commit()

    logger.info("*** LEAVING main.py TO RUN selenium_script.py ***")
    kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
    
    logger.info("*** LEAVING main.py TO webflow.py  ***")
    logger.info(f"running create_collection_item() with: bill_url{bill_url}, kialo_url{kialo_url}")
    webflow_item_id, slug = webflow_api.create_collection_item(bill_url, bill_details, kialo_url)
    webflow_url = f"https://digitaldemocracyproject.org/bills-copy/{slug}"

    logger.info("*** LEAVING webflow.py TO main.py  ***")
    # Update the newly created Bill instance with webflow_link
    new_bill.webflow_link = webflow_url
    db.commit()

    return JSONResponse(content={"message": "Bill processed successfully", "kialo_url": kialo_url, "webflow_item_id": webflow_item_id, "webflow_url": webflow_url}, status_code=200)
