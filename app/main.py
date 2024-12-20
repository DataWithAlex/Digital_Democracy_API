import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import boto3
import openai
from .bill_processing import fetch_bill_details, fetch_federal_bill_details, create_summary_pdf, create_federal_bill_summary
from .translation import translate_to_spanish
from .selenium_script import run_selenium_script
from .models import BillRequest, Bill, BillMeta, FormData, FormRequest, ProcessingStatus
from .webflow import WebflowAPI, generate_slug
from fastapi.responses import JSONResponse
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# AWS credentials
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_DEFAULT_REGION")

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

@app.post("/update-bill/", response_class=Response)
async def update_bill(request: FormRequest, db: Session = Depends(get_db)):
    history_value = f"{request.year}{request.bill_number}"
    logger.info(f"Starting update-bill() for bill: {history_value}")

    try:
        # Check if the history value exists
        existing_bill = db.query(Bill).filter(Bill.history == history_value).first()
        if existing_bill:
            logger.info(f"Bill with history {history_value} already exists")
            return JSONResponse(content={
                "message": "Bill already exists",
                "status": "success",
                "history_value": history_value
            }, status_code=200)

        # Return immediate acknowledgment
        response = JSONResponse(content={
            "message": "Request received successfully. Processing will continue in the background.",
            "status": "processing",
            "history_value": history_value
        }, status_code=202)

        # Start processing in background
        try:
            # New bill creation
            bill_url = f"https://www.flsenate.gov/Session/Bill/{request.year}/{request.bill_number}"
            bill_details = fetch_bill_details(bill_url)
            logger.info(f"Obtained bill details for: {bill_url}")

            if not all(k in bill_details for k in ["govId", "billTextPath", "pdf_path", "description"]):
                raise HTTPException(status_code=500, detail="Required bill details are missing")

            new_bill = Bill(
                govId=bill_details["govId"], 
                billTextPath=bill_details["billTextPath"], 
                history=history_value
            )
            db.add(new_bill)
            db.commit()

            pdf_path, summary, pros, cons = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
            logger.info("Generated summary")

            for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
                new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language="EN")
                db.add(new_meta)
            db.commit()

            logger.info("Running selenium script")
            kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
            if kialo_url is None:
                logger.warning("Selenium script failed but continuing")

            logger.info("Creating webflow item")
            result = webflow_api.create_live_collection_item(
                bill_url=bill_details["gov-url"],
                bill_details=bill_details,
                kialo_url=kialo_url,
                support_text=request.member_organization if request.support == "Support" else '',
                oppose_text=request.member_organization if request.support == "Oppose" else '',
                jurisdiction="FL",
                member_organization=request.member_organization
            )

            if result is None:
                logger.error("Failed to create webflow item")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create webflow item. Please ensure all Webflow collection changes are published."
                )

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

        except Exception as processing_error:
            logger.error(f"Background processing error: {str(processing_error)}")
            # The error will be visible in the status endpoint
            raise

        return response

    except HTTPException as http_exc:
        db.rollback()
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred: {str(e)}")
        if "collection needs to be published" in str(e).lower():
            raise HTTPException(
                status_code=409,  # Using 409 to indicate conflict
                detail=str(e)
            )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/bill-status/{history_value}")
async def get_bill_status(history_value: str, db: Session = Depends(get_db)):
    try:
        # Check if the bill exists
        bill = db.query(Bill).filter(Bill.history == history_value).first()
        
        if not bill:
            return JSONResponse(content={
                "message": "Bill not found",
                "status": "not_found"
            }, status_code=404)

        # If bill exists, it means processing was completed
        return JSONResponse(content={
            "message": "Bill processing completed",
            "status": "completed",
            "webflow_link": bill.webflow_link
        }, status_code=200)

    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        return JSONResponse(content={
            "message": "Error fetching status",
            "status": "error"
        }, status_code=500)
    finally:
        db.close()

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

@app.post("/process-federal-bill/", response_class=Response)
async def process_federal_bill(request: FormRequest, db: Session = Depends(get_db)):
    logger.info(f"Starting process-federal-bill() for bill: {request.bill_number} in session {request.session}")
    try:
        # Fetch bill details
        bill_details = fetch_federal_bill_details(request.session, request.bill_number, request.bill_type)
        logger.info(f"Obtained federal bill details for: {bill_details['govId']}")

        # Generate summary and PDFs
        pdf_path, summary, pros, cons = create_federal_bill_summary(
            bill_details['full_text'],
            language=request.lan,
            title=bill_details['title']
        )

        # Create new bill record
        new_bill = Bill(
            govId=bill_details['govId'],
            billTextPath=bill_details['billTextPath'],
            history=f"{request.session}{request.bill_type}{request.bill_number}"
        )
        db.add(new_bill)
        db.flush()

        # Add metadata
        for meta_type, text in [("Summary", summary), ("Pro", pros), ("Con", cons)]:
            new_meta = BillMeta(billId=new_bill.id, type=meta_type, text=text, language=request.lan)
            db.add(new_meta)
        db.commit()

        # Create Kialo discussion
        logger.info("Running selenium script for federal bill")
        kialo_url = run_selenium_script(title=bill_details['govId'], summary=summary, pros_text=pros, cons_text=cons)
        if kialo_url is None:
            logger.warning("Selenium script failed but continuing")

        # Create Webflow item
        logger.info("Creating webflow item")
        result = webflow_api.create_live_collection_item(
            bill_details['gov-url'],
            {
                **bill_details,
                "description": summary
            },
            kialo_url,
            support_text=request.member_organization if request.support == "Support" else '',
            oppose_text=request.member_organization if request.support == "Oppose" else '',
            jurisdiction="US",
            member_organization=request.member_organization
        )

        if result is None:
            logger.error("Failed to create webflow item")
            raise HTTPException(status_code=500, detail="Failed to create webflow item")

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
            legislation_type="Federal Bills",
            session=request.session,
            bill_number=request.bill_number,
            bill_type=request.bill_type,
            support=request.support,
            govId=bill_details["govId"],
            db=db
        )

        # Return PDF
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                return Response(content=pdf_file.read(), media_type="application/pdf")
        else:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JSONResponse(content={
            "message": "An error occurred while processing the request",
            "status": "error"
        }, status_code=500)
    finally:
        db.close()