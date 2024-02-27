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

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database connection details
db_host = 'ddp-api.czqcac8oivov.us-east-1.rds.amazonaws.com'
db_name = 'digital_democracy'
db_user = 'DataWithAlex'
db_password = '%Mineguy29'
db_port = 3306

# SQLAlchemy engine and session maker
engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
        run_selenium_script(
            title=bill_details['govId'],
            summary=summary,
            pros_text=pros,
            cons_text=cons
        )
        logger.info("Finished running Selenium script")

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

@app.post("/generate-bill-summary/", response_class=Response)
async def generate_bill_summary(bill_request: BillRequest, db: Session = Depends(get_db)):
    return process_bill_request(bill_request, db)

@app.post("/update-bill/", response_class=Response)
async def update_bill(year: str, bill_number: str, db: Session = Depends(get_db)):
    # Construct URL for the bill
    bill_url = f"https://www.flsenate.gov/Session/Bill/{year}/{bill_number}"
    
    # Invoke the process_bill_request function with the constructed URL and English language
    return process_bill_request(BillRequest(url=bill_url, lan="en"), db)
