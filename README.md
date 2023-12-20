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
The URL example above, https://www.flsenate.gov/Session/Bill/2023/23/ByCategory/?Tab=BillText , is a bill on FLsenate.gov:

![image](https://github.com/DataWithAlex/Digital_Democracy_API/assets/106262604/5398cd37-f8c5-4d3d-a1e7-f773efb360c3)

The API will return a JSON response indicating the success of the operation. The result is a PDF generated which contains a summary of the bill, and Pros & Cons for whether it was voted on or not:

![image](https://github.com/DataWithAlex/Digital_Democracy_API/assets/106262604/7bf71a29-ec45-43cb-9f78-142b358cdedc)


## API Endpoints

- POST /generate-bill-summary/: Generates a bill summary PDF report.

![image](https://github.com/DataWithAlex/Digital_Democracy_API/assets/106262604/57132440-d27b-425b-b2b1-eb67dd7a6329)


## How It Works

The API consists of several components:

- web_scraping.py: Contains logic to scrape bill details from the web.
- summarization.py: Interfaces with OpenAI to generate summaries.
- pdf_generation.py: Uses ReportLab and PyMuPDF to create a PDF report.
- main.py: The FastAPI application definition with API endpoints.

## License

Copyright (c) [2023] [Alex Sciuto]

All rights reserved.

No permission is granted to use, modify, or distribute this software or its parts for any purpose without the express written permission of the copyright owner.




