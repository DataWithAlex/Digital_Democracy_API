# Digital Democracy API

The Digital Democracy API is a FastAPI application designed to process legislative bills. It fetches bill details, generates summaries and pros/cons using OpenAI's API, and publishes the results to Kialo and Webflow. This application is deployed on an AWS EC2 instance, ensuring scalability and reliability.

## Features

- **Bill Retrieval**: Fetches bill details from the Florida Senate website or Congress.gov.
- **Summarization**: Utilizes OpenAI's API to generate concise summaries of bill content.
- **Pros and Cons Generation**: Analyzes bill content to produce a list of pros and cons.
- **PDF Report Creation**: Compiles summaries and pros/cons into a PDF report.
- **Publishing**: Publishes the report to Kialo for organizational interaction and to Webflow for public viewing.

## Architecture

The application is structured into several components, each responsible for a specific part of the workflow:

1. **Web Scraping**: Extracts bill details from the web.
   - Relevant script: `bill_processing.py` (startLine: 1, endLine: 33)

2. **Summarization**: Interfaces with OpenAI to generate summaries.
   - Relevant script: `bill_processing.py` (startLine: 278, endLine: 300)

3. **PDF Generation**: Uses ReportLab and PyMuPDF to create a PDF report.
   - Relevant script: `bill_processing.py` (startLine: 447, endLine: 477)

4. **API Definition**: The FastAPI application with defined endpoints.
   - Relevant script: `main.py` (startLine: 114, endLine: 177)

## Deployment

The application is deployed on an AWS EC2 instance, providing a robust environment for handling API requests. The deployment process involves:

1. **EC2 Setup**: Configure an EC2 instance with the necessary security groups and IAM roles.
2. **Environment Configuration**: Set environment variables for AWS credentials and OpenAI API keys.
3. **Service Management**: Use systemd to manage the FastAPI service, ensuring it runs continuously and restarts on failure.

## Local Development

### Prerequisites

- Python 3.8+
- Pip
- Virtual environment (optional but recommended)

### Installation

Clone the repository to your local machine:

git clone https://github.com/digital-democracy/digital-democracy-api.git
cd digital-democracy-api

(Optional) Create a virtual environment:

python3 -m venv venv
source venv/bin/activate  # For Unix or MacOS
venv\Scripts\activate  # For Windows

### Running API Locally

Set up environment variables for your OpenAI API key:

export OPENAI_API_KEY='your-api-key-here'

Start the FastAPI server with uvicorn:

uvicorn app.main:app --reload

## Usage

To generate a bill summary, send a POST request to `/process-federal-bill/` with a JSON body containing the bill details, for example:

{
  "name": "Sample Bill",
  "email": "user@example.com",
  "member_organization": "Sample Organization",
  "year": 2023,
  "session": "Regular",
  "bill_number": "1234",
  "bill_type": "Senate",
  "support": "Support",
  "govId": "SB1234"
}

The API will return a PDF containing a summary of the bill, and pros & cons for whether it was voted on or not.

## API Endpoints

- **POST /process-federal-bill/**: Processes a federal bill and generates a PDF report.
  - This endpoint receives a form request containing bill details. It fetches the bill text, generates a summary using OpenAI, and creates a new bill entry in the database. It also publishes the bill to Kialo and Webflow, and returns a PDF report.

- **POST /update-bill/**: Updates an existing bill with new information.
  - This endpoint updates the details of an existing bill in the database. It fetches the current bill details from Webflow, updates the bill with new information, and commits the changes to the database.

## How It Works

1. **Bill Submission**: Users submit a bill via the API.
   - Relevant code: `main.py` (startLine: 114, endLine: 177)

2. **Bill Processing**: Fetch bill details and generate summaries and pros/cons.
   - Relevant code: `bill_processing.py` (startLine: 278, endLine: 300)

3. **Publishing**: Publish the bill to Kialo and Webflow.
   - Relevant code: `main.py` (startLine: 147, endLine: 155)

4. **Logging and Monitoring**: Logs are generated for each step to facilitate debugging.

## Logging System

- **Centralized Logging**: All logs are configured in `logger_config.py`.
- **Log Levels**: Implement different logging levels (DEBUG, INFO, WARNING, ERROR) to capture various details.
- **Log Storage**: Store logs in a dedicated directory, e.g., `logs/`, and rotate them to prevent excessive disk usage.

## Folder Structure

- `app/`: Application code
- `tests/`: Test cases
- `docs/`: Documentation
- `config/`: Configuration files
- `logs/`: Log files

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request for review.

## License

This project is licensed under the MIT License