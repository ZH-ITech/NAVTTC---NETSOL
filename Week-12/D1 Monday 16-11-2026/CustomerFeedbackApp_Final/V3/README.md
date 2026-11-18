# Customer Feedback Intelligence — V3

A Flask-based customer feedback analytics application that transforms uploaded customer reviews into structured sentiment insights and executive-ready reports.

## 1. Project Overview

V3 builds on the earlier versions of Customer Feedback Intelligence.

Key capabilities:
- Upload and analyse customer feedback CSV files.
- Classify reviews as positive, neutral, or negative.
- Extract important review phrases using YAKE.
- Identify complaint categories using rule-based analysis.
- Display sentiment KPIs and product-level comparisons.
- Generate executive reports using validated Python-calculated facts.
- Download executive reports in Markdown format.
- Use a local template-based report generator without requiring an API key.
- Optionally use an OpenAI-powered narrative backend when configured.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Data processing | Pandas, NumPy |
| Sentiment analysis | VADER |
| Keyword extraction | YAKE |
| Reporting | Python templates and validation |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Charts | Chart.js |
| Optional AI reporting | OpenAI API |

## 3. Main Features

### Feedback Analysis
- CSV upload and validation.
- Sentiment classification.
- Keyword and phrase extraction.
- Complaint category detection.
- Product-level sentiment analysis.

### Analytics Dashboard
- Review volume and sentiment distribution.
- Positive, neutral, and negative percentages.
- Product comparisons.
- Interactive charts.
- CSV results download.

### Executive Reporting
- Structured executive summary.
- Key findings and complaint analysis.
- Business recommendations.
- Data limitations and caveats.
- Numerical claim validation against calculated facts.
- Markdown report download.

## 4. Project Structure

```text
V3/
├── app.py
├── analysis.py
├── backend_errors.py
├── categories.py
├── comparison.py
├── config.py
├── data_loader.py
├── distilbert_backend.py
├── kpis.py
├── nlp_backends.py
├── pipeline.py
├── report_facts.py
├── report_markdown.py
├── report_service.py
├── report_template.py
├── report_validate.py
├── requirements.txt
├── requirements-distilbert.txt
├── .env.example
├── data/
│   └── sample_feedback.csv
├── templates/
│   ├── base.html
│   ├── compare.html
│   ├── executive_report.html
│   ├── index.html
│   └── results.html
└── smoke_test_*.py

## 5. Installation

Open PowerShell in the V3 project directory.

Activate the existing virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Configuration

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Template-based reporting works without an OpenAI API key. OpenAI-powered reporting is optional.

Keep `.env` private. Never commit or share API keys.

## 7. Run the Application

```powershell
python app.py
```

Open the local development address printed by Flask. The default is:

http://127.0.0.1:5000

## 8. Run the Tests

```powershell
python smoke_test_report.py
python smoke_test_v2_data.py
python smoke_test_v2_app.py
python smoke_test_nlp.py
python smoke_test_report_app.py
```

## 9. Data Privacy and Reporting Integrity

- Executive-report facts are calculated by Python.
- Numerical claims are validated against the calculated fact sheet.
- Raw customer review text and customer identifiers are excluded from the executive-report fact sheet.
- API keys and local environment files must remain private.

## 10. Version Notes

V3 introduces validated executive reporting while retaining the feedback analysis, sentiment classification, and dashboard capabilities developed in earlier versions.

The template reporting backend provides a local fallback when an external AI service is not configured.
