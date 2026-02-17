# PDF Redactor

A simple web app for automatically detecting and redacting sensitive information from PDF documents.

## Features

- **Drag & drop** PDF upload
- **Auto-detect** common PII patterns:
  - Social Security Numbers (full, partial, last 4)
  - Dates of Birth
  - Phone Numbers
  - Email Addresses
  - Driver's License Numbers
  - Account Numbers
- **Visual preview** with highlighted matches
- **Select/deselect** individual items to redact
- **Manual redaction** for custom text
- **Download** redacted PDF with one click

## Live Demo

Try it at: [pdf-redactor.streamlit.app]([https://pdf-redactor.streamlit.app](https://pdf-redactor-awesome.streamlit.app))

## Run Locally

```bash
pip install streamlit pymupdf
streamlit run app.py
```

## How It Works

1. Upload a PDF
2. The app scans for text matching common PII patterns
3. Matches are highlighted in the preview and listed with checkboxes
4. Select which items to redact
5. Click "Redact" and download your clean PDF

Redactions are permanent — the text is removed from the PDF, not just covered up.

## Privacy

All processing happens locally in your browser session. No files are stored or transmitted to external servers.

## License

MIT
