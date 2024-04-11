import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from .web_scraping import fetch_bill_details
from .pdf_generation import create_summary_pdf, create_summary_pdf_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta
from .webflow import WebflowAPI
from fastapi.responses import JSONResponse

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    api_key= os.getenv("WEBFLOW_KEY"),
    collection_id= os.getenv("WEBFLOW_COLLECTION_KEY"),
    site_id= os.getenv("WEBFLOW_SITE_ID")
)

logger.info(f"WEBFLOW_KEY: {os.getenv('WEBFLOW_KEY')}")
logger.info(f"WEBFLOW_COLLECTION_KEY: {os.getenv('WEBFLOW_COLLECTION_KEY')}")
logger.info(f"WEBFLOW_SITE_ID: {os.getenv('WEBFLOW_SITE_ID')}")

# Exception handler
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return JSONResponse(content={"message": "An internal server error occurred."}, status_code=500)

# Process bill request
def process_bill_request(bill_request: BillRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate bill summary for URL: {bill_request.url}")
    try:
        # Fetch bill details
        logger.info(f"Fetching bill details from URL: {bill_request.url}")
        bill_details = fetch_bill_details(bill_request.url)

        # Log bill details
        logger.info("Bill details:")
        for key, value in bill_details.items():
            logger.info(f"{key}: {value}")

        # Ensure required keys are present
        required_keys = ["govId", "billTextPath", "pdf_path"]
        if not all(key in bill_details for key in required_keys):
            raise HTTPException(status_code=500, detail="Required bill details are missing.")

        # Generate PDF and summary
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

        # Run Selenium script
        logger.info("Running Selenium script")
        kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
        logger.info(f"Finished running Selenium script. Kialo URL: {kialo_url}")

        # Update bill_details with summary for Webflow item creation
        bill_details['description'] = summary
        logger.info(f"Summary for Webflow: {summary}")

        # Create Webflow item
        logger.info("Creating Webflow item")
        webflow_item_id = webflow_api.create_collection_item(bill_request.url, bill_details, kialo_url)

        # Check if PDF was successfully created
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

# Update bill
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
    logger.info(f"Obtained bill details for: {bill_url}")

    # Ensure required keys are present
    if not all(k in bill_details for k in ["govId", "billTextPath", "pdf_path"]):
        raise HTTPException(status_code=500, detail="Required bill details are missing.")

    # Insert bill details into the database
    new_bill = Bill(govId=bill_details["govId"], billTextPath=bill_details["billTextPath"], history=history_value)
    db.add(new_bill)
    db.commit()

    # Generate PDF and summary
    pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
    logger.info("Generated Summary")

    # Insert summary, pros, and cons into bill_meta
    for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
        new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language="EN")
        db.add(new_meta)
    db.commit()

    # Run Selenium script
    logger.info("Running Selenium script")
    kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)

    # Create Webflow item
    logger.info("Creating Webflow item")
    webflow_item_id, slug = webflow_api.create_collection_item(bill_url, bill_details, kialo_url)
    webflow_url = f"https://digitaldemocracyproject.org/bills-copy/{slug}"

    # Update the newly created Bill instance with webflow_link
    new_bill.webflow_link = webflow_url
    db.commit()

    return JSONResponse(content={"message": "Bill processed successfully", "kialo_url": kialo_url, "webflow_item_id": webflow_item_id, "webflow_url": webflow_url}, status_code=200)
