# Digital Democracy API

The Digital Democracy API is a FastAPI application designed to summarize legislative bills and generate a report with pros and cons based on the bill's content. This API interfaces with the OpenAI API to perform the summarization.

## Features

- Fetch bill details from the Florida Senate website.
- Summarize the bill content into a comprehensive summary.
- Generate pros and cons for supporting the bill.
- Create a PDF report with the summary and pros/cons.

## Local Development

### Prerequisites

- Python 3.8+
- Pip
- Virtual environment (optional but recommended)

### Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/your-github-username/digital-democracy-api.git
cd digital-democracy-api
```
(Optional) Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # For Unix or MacOS
venv\Scripts\activate  # For Windows
```

## Runnning API Locally

Set up environment variables for your OpenAI API key:

```bash
export OPENAI_API_KEY='your-api-key-here'
```
Start the FastAPI server with uvicorn:

```bash
uvicorn app.main:app --reload
```
## Usage

To generate a bill summary, send a POST request to /generate-bill-summary/ with a JSON body containing the bill URL, for example:

```JSON
{
  "url": "https://www.flsenate.gov/Session/Bill/2023/23/ByCategory/?Tab=BillText"
}

```
The API will return a JSON response indicating the success of the operation.

## API Endpoints

- POST /generate-bill-summary/: Generates a bill summary PDF report.

## How It Works

The API consists of several components:

- web_scraping.py: Contains logic to scrape bill details from the web.
- summarization.py: Interfaces with OpenAI to generate summaries.
- pdf_generation.py: Uses ReportLab and PyMuPDF to create a PDF report.
- main.py: The FastAPI application definition with API endpoints.

## License
MIT License



