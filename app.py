"""
PDF Redactor - User-friendly PII redaction tool
"""
import streamlit as st
import fitz  # PyMuPDF
import re
import io
import base64
from pathlib import Path

# Page config
st.set_page_config(
    page_title="PDF Redactor",
    page_icon="🔒",
    layout="wide"
)

# Custom CSS for cleaner look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .match-box {
        background: #FFF3CD;
        border-left: 4px solid #FFC107;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .redacted-box {
        background: #D4EDDA;
        border-left: 4px solid #28A745;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .stButton > button {
        width: 100%;
        background-color: #1E3A5F;
        color: white;
        font-weight: 600;
        padding: 0.75rem 1rem;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background-color: #2E5A8F;
    }
    .upload-section {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# PII patterns for voter registration forms
PII_PATTERNS = {
    "SSN (Full)": r"\b\d{3}-\d{2}-\d{4}\b",
    "SSN (Partial)": r"\b[X*]{3,5}-?[X*]{2}-?\d{4}\b|\b\d{3}-?[X*]{2}-?[X*]{4}\b",
    "SSN (Last 4)": r"\b(?:SSN|SS#?|Social)[\s:]*[X*]*\d{4}\b",
    "Date of Birth": r"\b(?:DOB|Date of Birth|Birth Date|Born)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "Date (MM/DD/YYYY)": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "Driver's License": r"\b(?:DL|Driver'?s?\s*License|License\s*#?)[\s:]*[A-Z]?\d{6,12}\b",
    "Phone Number": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "Account Number": r"\b(?:Account|Acct)[\s#:]*[X*]*\d{4,}\b|\b[X*]{4,}\d{4}\b",
}

def find_pii_in_text(text):
    """Find all PII matches in text"""
    matches = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append({
                "type": pii_type,
                "text": match.group(),
                "start": match.start(),
                "end": match.end()
            })
    return matches

def find_pii_in_pdf(pdf_bytes):
    """Find all PII in a PDF document"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_matches = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        matches = find_pii_in_text(text)
        for match in matches:
            match["page"] = page_num + 1
            # Find location in PDF
            rects = page.search_for(match["text"])
            match["rects"] = rects
            all_matches.append(match)
    
    doc.close()
    return all_matches

def redact_pdf(pdf_bytes, items_to_redact):
    """Apply redactions to PDF"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for item in items_to_redact:
        page = doc[item["page"] - 1]
        for rect in item["rects"]:
            page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()
    
    # Save to bytes
    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    output.seek(0)
    return output.getvalue()

def render_pdf_preview(pdf_bytes, page_num=0, highlights=None):
    """Render a PDF page as image with optional highlights"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    
    # Highlight areas if provided
    if highlights:
        for h in highlights:
            if h.get("page") == page_num + 1:
                for rect in h.get("rects", []):
                    page.draw_rect(rect, color=(1, 1, 0), fill=(1, 1, 0), fill_opacity=0.3)
    
    # Render at good resolution
    mat = fitz.Matrix(1.5, 1.5)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    page_count = doc.page_count
    doc.close()
    return img_bytes, page_count

# Main UI
st.markdown('<p class="main-header">🔒 PDF Redactor</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automatically find and redact sensitive information from PDFs</p>', unsafe_allow_html=True)

# File upload
uploaded_file = st.file_uploader(
    "Drop your PDF here or click to browse",
    type=["pdf"],
    help="Upload a PDF file to scan for sensitive information"
)

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    
    # Store in session state
    if "pdf_bytes" not in st.session_state or st.session_state.get("filename") != uploaded_file.name:
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.filename = uploaded_file.name
        st.session_state.matches = find_pii_in_pdf(pdf_bytes)
        st.session_state.selected = {i: True for i in range(len(st.session_state.matches))}
    
    matches = st.session_state.matches
    
    # Layout: two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Document Preview")
        
        # Page selector
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = doc.page_count
        doc.close()
        
        if total_pages > 1:
            page_num = st.slider("Page", 1, total_pages, 1) - 1
        else:
            page_num = 0
        
        # Get highlights for current page
        highlights = [m for m in matches if m["page"] == page_num + 1 and st.session_state.selected.get(matches.index(m), True)]
        
        # Render preview
        img_bytes, _ = render_pdf_preview(pdf_bytes, page_num, highlights)
        st.image(img_bytes, use_container_width=True)
    
    with col2:
        st.subheader(f"🔍 Found {len(matches)} Potential PII Items")
        
        if matches:
            # Group by type
            by_type = {}
            for i, m in enumerate(matches):
                t = m["type"]
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append((i, m))
            
            # Select all / none
            scol1, scol2, scol3 = st.columns(3)
            with scol1:
                if st.button("✅ Select All"):
                    st.session_state.selected = {i: True for i in range(len(matches))}
                    st.rerun()
            with scol2:
                if st.button("❌ Clear All"):
                    st.session_state.selected = {i: False for i in range(len(matches))}
                    st.rerun()
            with scol3:
                selected_count = sum(1 for v in st.session_state.selected.values() if v)
                st.markdown(f"**{selected_count}** selected")
            
            st.divider()
            
            # Show by type
            for pii_type, items in by_type.items():
                with st.expander(f"**{pii_type}** ({len(items)} found)", expanded=True):
                    for idx, match in items:
                        col_a, col_b = st.columns([0.1, 0.9])
                        with col_a:
                            checked = st.checkbox(
                                "sel",
                                value=st.session_state.selected.get(idx, True),
                                key=f"check_{idx}",
                                label_visibility="hidden"
                            )
                            st.session_state.selected[idx] = checked
                        with col_b:
                            st.markdown(f'`{match["text"]}` — Page {match["page"]}')
            
            st.divider()
            
            # Redact button
            selected_items = [matches[i] for i, sel in st.session_state.selected.items() if sel]
            
            if st.button(f"🔒 Redact {len(selected_items)} Selected Items", type="primary", disabled=len(selected_items)==0):
                with st.spinner("Applying redactions..."):
                    redacted_pdf = redact_pdf(pdf_bytes, selected_items)
                    st.session_state.redacted_pdf = redacted_pdf
                    st.success(f"✅ Redacted {len(selected_items)} items!")
            
            # Download button
            if "redacted_pdf" in st.session_state:
                st.download_button(
                    label="⬇️ Download Redacted PDF",
                    data=st.session_state.redacted_pdf,
                    file_name=f"redacted_{uploaded_file.name}",
                    mime="application/pdf"
                )
        else:
            st.info("No sensitive information detected. You can still manually add items to redact.")
        
        # Manual redaction
        st.divider()
        st.subheader("✏️ Manual Redaction")
        custom_text = st.text_input("Enter text to redact:", placeholder="Type exact text to find and redact...")
        
        if custom_text and st.button("Add to Redaction List"):
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            found = False
            for page_num, page in enumerate(doc):
                rects = page.search_for(custom_text)
                if rects:
                    new_match = {
                        "type": "Manual",
                        "text": custom_text,
                        "page": page_num + 1,
                        "rects": rects
                    }
                    st.session_state.matches.append(new_match)
                    st.session_state.selected[len(st.session_state.matches)-1] = True
                    found = True
            doc.close()
            if found:
                st.success(f"Added '{custom_text}' to redaction list")
                st.rerun()
            else:
                st.warning(f"Text '{custom_text}' not found in document")

else:
    # Show instructions when no file uploaded
    st.markdown("""
    ### How it works:
    
    1. **Upload** a PDF document
    2. **Review** automatically detected sensitive information
    3. **Select** which items to redact (or add custom text)
    4. **Download** your redacted PDF
    
    ---
    
    ### What we detect:
    - 🔢 Social Security Numbers (full, partial, last 4)
    - 📅 Dates of Birth
    - 🪪 Driver's License Numbers
    - 📞 Phone Numbers
    - 📧 Email Addresses
    - 🏦 Account Numbers
    
    ---
    
    *Your documents are processed locally and never stored.*
    """)
