from fastapi import FastAPI, HTTPException
from app.web_scraping import fetch_bill_details
from app.pdf_generation import create_summary_pdf
from app.summarization import full_summarize_with_openai_chat
from app.models import BillRequest

app = FastAPI()

@app.post("/generate-bill-summary/")
async def generate_bill_summary(bill_request: BillRequest):
    try:
        # Fetch bill details
        bill_details = fetch_bill_details(bill_request.url)
        
        # Check if PDF path exists in the response
        if 'pdf_path' in bill_details:
            # Summarize and generate PDF
            create_summary_pdf(bill_details['pdf_path'], "output/bill_summary.pdf", bill_details['title'])
            return {"message": "Bill summary generated successfully"}
        else:
            raise HTTPException(status_code=404, detail="PDF not found for the bill")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



