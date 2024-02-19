from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from .web_scraping import fetch_bill_details
from .pdf_generation import create_summary_pdf, create_summary_pdf_spanish
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta
import logging
import os
import re
import openai

from .logger_config import logger

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

# FastAPI app initialization
app = FastAPI()

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Exception handlers
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return {"message": "An internal server error occurred."}

@app.post("/generate-bill-summary/", response_class=Response)
async def generate_bill_summary(bill_request: BillRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to generate bill summary for URL: {bill_request.url}")
    try:
        # Fetch bill details
        bill_details = fetch_bill_details(bill_request.url)

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

# Additional functions for storing bill details in the database
def insert_bill_details_to_db(bill_details, pros, cons, summary):
    db = SessionLocal()
    try:
        # Insert into bill table
        new_bill = Bill(govId=bill_details["govId"], billTextPath=bill_details["billTextPath"])
        db.add(new_bill)
        db.commit()
        db.refresh(new_bill)

        # Insert into bill_meta table
        for item in [("Pro", pros), ("Con", cons), ("Summary", summary)]:
            new_meta = BillMeta(billId=new_bill.id, type=item[0], text=item[1], language="EN")
            db.add(new_meta)
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in inserting bill details to DB: {e}")
    finally:
        db.close()
