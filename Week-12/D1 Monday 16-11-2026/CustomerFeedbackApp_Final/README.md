
# Customer Feedback Intelligence

A Python and Flask-based application that transforms customer reviews into structured feedback insights using Natural Language Processing (NLP).

This project includes two versions, progressing from individual review analysis to a dataset-driven customer feedback dashboard.

## Project Versions

### V1 - Single Review Analysis

The original application focuses on analysing individual customer reviews.

Features:
- Individual customer review analysis.
- Sentiment detection using VADER.
- Key phrase extraction using YAKE.
- Rule-based complaint category detection.
- Review text validation.
- Flask web interface.
- Application health-check endpoint.

### V2 - Customer Feedback Intelligence Dashboard

The enhanced version introduces dataset-level feedback analysis.

Features:
- Upload customer feedback datasets in CSV format.
- Analyse the included sample dataset.
- Validate CSV structure and input data.
- Process multiple customer reviews.
- Calculate key performance indicators (KPIs).
- Display analysis results and charts.
- Show data-processing warnings.
- Export analysed results to CSV.
- Analyse individual reviews.
- Application health-check endpoint.
- Configurable upload, row-count, and review-length limits.

## Optional DistilBERT Backend (V2b)

V2 can optionally use DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`) instead of VADER. It is local and optional, and needs PyTorch (about 1.6 GB including the model cache).

Install it from the V2 folder with `python -m pip install -r requirements-distilbert.txt --no-cache-dir`.

- DistilBERT is an English **binary** model. It returns Positive or Negative only, never Neutral, so the dashboard shows Neutral as `n/a` for this backend.
- It was fine-tuned on movie-review sentences, not product reviews, and its confidence is not a measure of correctness.
- The model downloads once into `V2/.hf_cache` (ignored by Git) and then runs offline.
- If DistilBERT cannot load, the whole dataset falls back to VADER and the results page says so.
- The **Compare VADER and DistilBERT** page shows both backends side by side. It measures agreement, not accuracy, because no human-labelled ground truth exists.
- The average score is backend-specific (VADER compound score versus DistilBERT signed confidence) and the two are not comparable.

Extra tests, run from `V2`: `python smoke_test_distilbert.py` and `python smoke_test_v2b_web.py`.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Flask | Web application framework |
| Pandas | Data processing and analysis |
| VADER Sentiment | Sentiment analysis |
| YAKE | Keyword extraction |
| NumPy | Numerical operations |
| Jinja2 | HTML template rendering |
| python-dotenv | Environment configuration |
| HTML / CSS | User interface |

## Project Structure

```text
CustomerFeedbackApp_Final/
|
|-- README.md
|-- .gitignore
|
|-- V1/
|   |-- app.py
|   |-- analysis.py
|   |-- categories.py
|   |-- config.py
|   |-- nlp_backends.py
|   |-- requirements.txt
|   |-- .env.example
|   |-- smoke_test_nlp.py
|   |-- data/
|   |   `-- sample_feedback.csv
|   `-- templates/
|       `-- index.html
|
`-- V2/
    |-- app.py
    |-- analysis.py
    |-- categories.py
    |-- config.py
    |-- data_loader.py
    |-- kpis.py
    |-- nlp_backends.py
    |-- pipeline.py
    |-- requirements.txt
    |-- .env.example
    |-- smoke_test_nlp.py
    |-- smoke_test_v2_app.py
    |-- smoke_test_v2_data.py
    |-- data/
    |   `-- sample_feedback.csv
    `-- templates/
        |-- base.html
        |-- index.html
        `-- results.html
```

## Requirements

- Windows, Linux, or macOS.
- Python 3.11 recommended (developed and tested with 3.11).
- pip package manager.
- Modern web browser.

Each version has its own `requirements.txt` and environment configuration.

## Installation and Setup

### 1. Navigate to V2

```powershell
cd "CustomerFeedbackApp_Final\V2"
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Default V2 configuration:

| Variable | Example value | Purpose |
|---|---:|---|
| FLASK_DEBUG | 1 | Flask debug setting |
| MAX_UPLOAD_MB | 5 | Maximum upload size |
| MAX_ROWS | 2000 | Maximum CSV data rows |
| MIN_REVIEW_CHARS | 3 | Minimum review length |
| MAX_REVIEW_CHARS | 1000 | Maximum review length |

Adjust these settings in `.env` when necessary.

Do not commit private environment files or secrets.

## Running the Application

Run V2 from its project directory:

```powershell
python app.py
```

Open the dashboard:

http://127.0.0.1:5000

Health-check endpoint:

http://127.0.0.1:5000/health

### Running V1

Stop the V2 application first, then open another PowerShell terminal:

```powershell
cd "CustomerFeedbackApp_Final\V1"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open:

http://127.0.0.1:5000

**Important:** Both versions use port 5000 by default. Run them separately unless you change the port configuration.

## Using the V2 Dashboard

1. Start the Flask application.
2. Open the dashboard in your browser.
3. Select the bundled sample dataset or upload a CSV file.
4. Select an available sentiment analysis backend.
5. Submit the dataset for analysis.
6. Review the KPIs, charts, results, and processing messages.
7. Download the analysed results as a CSV file.

## CSV Input Format

V2 requires these three columns:

| Column | Description |
|---|---|
| customer_id | Customer identifier |
| product | Product associated with the feedback |
| feedback | Customer review or comment |

Example:

```csv
customer_id,product,feedback
C001,Laptop,"Excellent laptop, very fast and reliable."
C002,Mobile,"The battery drains very quickly."
C003,Headphones,"Amazing sound quality and comfortable."
C004,Laptop,"Delivery was delayed by four days."
```

Sample dataset:

`V2/data/sample_feedback.csv`

Input handling includes:
- CSV header normalisation.
- UTF-8 and CP1252 encoding support.
- Comma-separated and semicolon-separated input.
- Empty feedback removal.
- Missing product and customer ID handling.
- Duplicate customer ID warnings.
- Configurable maximum row count.

## Testing

Run the following commands from the relevant version directory.

### V1 Tests

```powershell
python smoke_test_nlp.py
```

### V2 Tests

```powershell
python smoke_test_nlp.py
python smoke_test_v2_data.py
python smoke_test_v2_app.py
```

These scripts cover NLP functionality, CSV data handling, and application behaviour.

## Implementation Notes and Limitations

- VADER is primarily designed for English-language sentiment analysis. Non-English results should be interpreted cautiously.
- Complaint categories are identified using predefined keyword rules and may not recognise every expression or context.
- Automated sentiment results are indicators, not definitive measures of customer satisfaction.
- V2 stores analysis results in application memory. Results may become unavailable after the server restarts.
- Flask debug mode is intended for local development and should be disabled in production.
- Avoid uploading sensitive personal information in demonstration datasets.

## Future Improvements

Potential enhancements include:

- Advanced multilingual sentiment analysis.
- Improved complaint classification.
- Persistent storage of analysis history.
- User authentication and role-based access.
- Additional dashboard filters and reporting.
- Production deployment and monitoring.
- Performance testing with larger datasets.

## GitHub Repository

https://github.com/ZH-ITech/NAVTTC---NETSOL

## Project Purpose

This project demonstrates practical Python development, NLP integration, CSV data processing, Flask application development, and the evolution of a single-review analysis tool into a structured customer feedback intelligence dashboard.


