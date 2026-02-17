# PDF Redactor

A user-friendly tool for automatically detecting and redacting sensitive information from PDFs.

## Features

- **Drag & drop** PDF upload
- **Auto-detect** common PII:
  - Social Security Numbers (full, partial, last 4)
  - Dates of Birth
  - Driver's License Numbers
  - Phone Numbers
  - Email Addresses
  - Account Numbers
- **Visual preview** with highlighted matches
- **Select/deselect** individual items
- **Manual redaction** for custom text
- **Download** redacted PDF

## Quick Start

```bash
cd /home/crackypp/projects/pdf-redactor
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Running on LAN

To access from other devices on your network:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then access via http://YOUR_PI_IP:8501

## Requirements

- Python 3.8+
- streamlit
- pymupdf (fitz)

Install with:
```bash
pip3 install streamlit pymupdf
```
