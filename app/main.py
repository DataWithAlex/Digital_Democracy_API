
from fastapi import FastAPI, HTTPException, Response
from app.web_scraping import fetch_bill_details
from app.pdf_generation import create_summary_pdf
from app.models import BillRequest
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.post("/generate-bill-summary/")
async def generate_bill_summary(bill_request: BillRequest):
    try:
        # Fetch bill details
        bill_details = fetch_bill_details(bill_request.url)
        
        # Check if PDF path exists in the response
        if 'pdf_path' in bill_details:
            # Summarize and generate PDF
            output_pdf_path = "output/bill_summary.pdf"
            create_summary_pdf(bill_details['pdf_path'], output_pdf_path, bill_details['title'])

            # Read the generated PDF and return as response
            with open(output_pdf_path, "rb") as file:
                pdf_content = file.read()
            return Response(content=pdf_content, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=bill_summary.pdf"})
        else:
            raise HTTPException(status_code=404, detail="PDF not found for the bill")
    except Exception as e:
        logging.error(f"Error generating bill summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))