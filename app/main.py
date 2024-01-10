from fastapi import FastAPI, HTTPException, Request, Response
from app.web_scraping import fetch_bill_details
from app.pdf_generation import create_summary_pdf
from app.models import BillRequest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    return {"message": "An internal server error occurred."}

@app.post("/generate-bill-summary/", response_class=Response)
async def generate_bill_summary(bill_request: BillRequest):
    try:
        # Fetch bill details
        bill_details = fetch_bill_details(bill_request.url)
        
        # Check if PDF path exists in the response
        if 'pdf_path' in bill_details:
            # Summarize and generate PDF
            pdf_path = create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
            
            # Read and return the PDF file
            with open(pdf_path, "rb") as pdf_file:
                return Response(content=pdf_file.read(), media_type="application/pdf")

        else:
            raise HTTPException(status_code=404, detail="PDF not found for the bill")
    except HTTPException as http_exc:
        logging.error(f"HTTP exception occurred: {http_exc}", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
