# Lead Generation Process

This repository brings together multiple internship deliverables focused on AI-assisted lead generation.

At a high level, the repo contains two major solution tracks:

1. `EDXSO school lead generation`
   Reads newly published CBSE circulars, classifies them by business relevance, maps them to EDXSO services, and produces outreach-ready proposals.

2. `Dynamic business lead generation`
   Ingests a company knowledge base from a Google Drive folder, uses that context to solve business problems or identify opportunities, and generates stakeholder-ready proposal emails with PDF attachments.

## What Is In This Repo

### 1. EDXSO CBSE lead generator

The EDXSO workflow is built around CBSE compliance and academic circular monitoring.

- `app.py`
  Base pipeline version. Scrapes CBSE circular sources, extracts PDF text, generates EDXSO proposals with Gemini, saves raw circular text into `cbse_circulars/`, saves proposal text into `edxso_proposals/`, and emails the final brief as HTML + PDF.

- `final_app.py`
  More polished EDXSO version with a Streamlit UI and optional Google Drive knowledge-base ingestion. This version keeps most processing in memory, loads official EDXSO docs from a Drive folder, and uses that extra context to generate more grounded proposals.

- `cbse_circulars/`
  Saved text extracted from CBSE circular PDFs.

- `edxso_proposals/`
  Generated proposal outputs based on those circulars.

- `last_circular_state.json`
  A simple state tracker used to avoid reprocessing circulars that were already handled.

### 2. Dynamic business lead generator

This is the more general and fully dynamic deliverable in the repo.

- `streamlit_app.py`
  Main Streamlit application for the dynamic business engine. It:
  ingests a Google Drive folder as a company knowledge base,
  reads PDF/DOCX/PPTX files,
  generates a concise understanding of the business,
  accepts a business problem statement,
  uses Gemini with Google Search for live research when needed,
  and emails a formatted PDF proposal to a stakeholder.

- `Conversely_Docs/`
  Example source material used as a business knowledge base for the dynamic lead-generation workflow.

- `test_conversely.py`
  Prototype/test script for the business-lead idea. It reads local company docs, scrapes a startup website, and generates a targeted outreach pitch.

### 3. Supporting / working files

- `Scrapper_Testing.ipynb`
  Working notebook used during development and testing of the scraping and proposal-generation flow.

- `requirements.txt`
  Python dependencies used across the scripts and Streamlit apps.

- `.env`
  Local environment variable file for API keys and email credentials. This file is intentionally not documented with values here.

## Core Workflows

### EDXSO workflow

1. Fetch CBSE updates from the academic circular page and the CBSE noticeboard.
2. Identify unprocessed PDF circulars.
3. Extract text from each circular.
4. Ask Gemini to classify the circular as a high-priority `Painkiller` or low-priority `Vitamin`.
5. Generate an outreach strategy aligned to EDXSO services or a goodwill advisory.
6. Optionally email a formatted internal brief with a PDF attachment.

### Dynamic business workflow

1. Accept a shareable Google Drive folder link.
2. Read supported knowledge-base files from the folder.
3. Build an in-memory company context.
4. Accept a user problem statement such as:
   finding tenders,
   researching competitors,
   identifying leads,
   or generating a pitch strategy.
5. Use Gemini plus live search to produce a business-focused strategic response.
6. Convert the result into a styled PDF and email it to a stakeholder.

## Tech Stack

- Python
- Streamlit
- Google Gemini via `google-genai`
- Google Drive API via `google-api-python-client`
- `requests` + `BeautifulSoup` for scraping
- `PyPDF2`, `python-docx`, and `python-pptx` for document parsing
- `trafilatura` for website text extraction
- `markdown` + `xhtml2pdf` for HTML/PDF proposal generation
- SMTP for email dispatch

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

Different scripts expect slightly different variable names, so keep the following available where relevant:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_DRIVE_API_KEY=your_google_drive_api_key

EMAIL_APP_PASSWORD=your_gmail_app_password

EMAIL_SENDER=sender@example.com
EMAIL_RECEIVER=receiver@example.com

SENDER_EMAIL=sender@example.com
```

Notes:

- `app.py` and `final_app.py` use `EMAIL_SENDER`, `EMAIL_RECEIVER`, and `EMAIL_APP_PASSWORD`.
- `streamlit_app.py` uses `SENDER_EMAIL` and `EMAIL_APP_PASSWORD`.
- The Google Drive folder used for knowledge-base ingestion should be accessible through the configured Drive API key.

## How To Run

### Run the EDXSO CLI pipeline

```bash
python app.py
```

### Run the EDXSO Streamlit app

```bash
streamlit run final_app.py
```

### Run the dynamic business lead generator

```bash
streamlit run streamlit_app.py
```

### Run the earlier Conversely prototype

```bash
python test_conversely.py
```

## Recommended Entry Points

If you are exploring this repo for the first time, start here:

- `final_app.py` for the EDXSO school/compliance lead-generation deliverable
- `streamlit_app.py` for the fully dynamic business lead-generation deliverable

## Repo Structure

```text
.
|-- app.py
|-- final_app.py
|-- streamlit_app.py
|-- test_conversely.py
|-- Scrapper_Testing.ipynb
|-- requirements.txt
|-- last_circular_state.json
|-- cbse_circulars/
|-- edxso_proposals/
|-- Conversely_Docs/
`-- .env
```

## Important Notes

- This repo mixes prototypes, working notebooks, generated outputs, and final deliverables in one place.
- The EDXSO side is domain-specific to school leads driven by CBSE circulars.
- The dynamic business engine is broader and can adapt to different companies as long as a usable knowledge base is supplied through Google Drive.
- Email delivery is built around Gmail SMTP and app-password based authentication.

## Summary

This repository documents the evolution from a focused CBSE-to-school lead engine for EDXSO into a more general agentic business lead generator. The first solution turns regulatory and academic circulars into targeted school outreach. The second turns any company knowledge base into a dynamic strategy and proposal engine that can research, reason, and generate outbound business material.