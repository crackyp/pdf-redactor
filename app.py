"""
PDF Redactor - User-friendly PII redaction tool
With authentication and premium features
"""
import streamlit as st
import fitz  # PyMuPDF
import re
import io
from supabase import create_client
import stripe

# Page config
st.set_page_config(
    page_title="PDF Redactor",
    page_icon="🔒",
    layout="wide"
)

# Initialize Supabase and Stripe from secrets
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

def init_stripe():
    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

supabase = init_supabase()
init_stripe()

# Custom CSS
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
    .premium-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .free-badge {
        background: #e0e0e0;
        color: #666;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
    }
    .upgrade-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# PII patterns for detection
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

# Premium-only patterns (AI-enhanced in future)
PREMIUM_PATTERNS = {
    "Street Address": r"\b\d{1,5}\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir)\b",
    "Zip Code": r"\b\d{5}(?:-\d{4})?\b",
    "Credit Card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
}

# ============ AUTH FUNCTIONS ============

def get_user_tier(user_id):
    """Fetch user's subscription tier from database"""
    try:
        result = supabase.table("users").select("tier").eq("id", user_id).single().execute()
        if result.data:
            return result.data.get("tier", "free")
    except:
        pass
    return "free"

def create_user_record(user_id, email):
    """Create user record in database if it doesn't exist"""
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "email": email,
            "tier": "free"
        }).execute()
    except:
        pass

def create_checkout_session(email, user_id):
    """Create Stripe checkout session for premium upgrade"""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email,
            client_reference_id=user_id,
            line_items=[{
                "price": st.secrets["STRIPE_PRICE_ID"],
                "quantity": 1,
            }],
            success_url=st.secrets["APP_URL"] + "?payment=success",
            cancel_url=st.secrets["APP_URL"] + "?payment=canceled",
        )
        return session.url
    except Exception as e:
        st.error(f"Error creating checkout: {e}")
        return None

def show_auth_page():
    """Display login/signup page"""
    st.markdown('<p class="main-header">🔒 PDF Redactor</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Sign in to redact sensitive information from PDFs</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted and email and password:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    if res.user:
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
    
    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pw")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up", use_container_width=True)
            
            if submitted:
                if not new_email or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    try:
                        res = supabase.auth.sign_up({
                            "email": new_email,
                            "password": new_password
                        })
                        if res.user:
                            create_user_record(res.user.id, new_email)
                            st.success("Account created! Please check your email to confirm, then login.")
                    except Exception as e:
                        st.error(f"Signup failed: {str(e)}")

# ============ PDF FUNCTIONS ============

def find_pii_in_text(text, include_premium=False):
    """Find all PII matches in text"""
    patterns = PII_PATTERNS.copy()
    if include_premium:
        patterns.update(PREMIUM_PATTERNS)
    
    matches = []
    for pii_type, pattern in patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append({
                "type": pii_type,
                "text": match.group(),
                "start": match.start(),
                "end": match.end()
            })
    return matches

def find_pii_in_pdf(pdf_bytes, include_premium=False):
    """Find all PII in a PDF document"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_matches = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        matches = find_pii_in_text(text, include_premium)
        for match in matches:
            match["page"] = page_num + 1
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
    
    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    output.seek(0)
    return output.getvalue()

def render_pdf_preview(pdf_bytes, page_num=0, highlights=None):
    """Render a PDF page as image with optional highlights"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    
    if highlights:
        for h in highlights:
            if h.get("page") == page_num + 1:
                for rect in h.get("rects", []):
                    page.draw_rect(rect, color=(1, 1, 0), fill=(1, 1, 0), fill_opacity=0.3)
    
    mat = fitz.Matrix(1.5, 1.5)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    page_count = doc.page_count
    doc.close()
    return img_bytes, page_count

# ============ MAIN APP ============

def show_main_app(user, is_premium):
    """Display the main PDF redactor app"""
    
    # Header with user info
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<p class="main-header">🔒 PDF Redactor</p>', unsafe_allow_html=True)
    with col2:
        if is_premium:
            st.markdown('<span class="premium-badge">⭐ Premium</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="free-badge">Free Plan</span>', unsafe_allow_html=True)
    with col3:
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
    
    # Upgrade prompt for free users
    if not is_premium:
        with st.expander("⭐ Upgrade to Premium", expanded=False):
            st.markdown("""
            **Premium features:**
            - 🏠 Address detection
            - 💳 Credit card detection  
            - 📮 Zip code detection
            - 📄 Batch processing (coming soon)
            - 🤖 AI-powered detection (coming soon)
            
            **$9/month** — Cancel anytime
            """)
            if st.button("Upgrade Now", type="primary"):
                checkout_url = create_checkout_session(user.email, user.id)
                if checkout_url:
                    st.markdown(f'<a href="{checkout_url}" target="_blank">Click here to complete payment</a>', unsafe_allow_html=True)
    
    # Check for payment success
    query_params = st.query_params
    if query_params.get("payment") == "success":
        st.success("🎉 Payment successful! Your premium features are now active.")
        st.query_params.clear()
    
    st.divider()
    
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
            st.session_state.matches = find_pii_in_pdf(pdf_bytes, include_premium=is_premium)
            st.session_state.selected = {i: True for i in range(len(st.session_state.matches))}
        
        matches = st.session_state.matches
        
        # Layout: two columns
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📄 Document Preview")
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = doc.page_count
            doc.close()
            
            if total_pages > 1:
                page_num = st.slider("Page", 1, total_pages, 1) - 1
            else:
                page_num = 0
            
            highlights = [m for m in matches if m["page"] == page_num + 1 and st.session_state.selected.get(matches.index(m), True)]
            
            img_bytes, _ = render_pdf_preview(pdf_bytes, page_num, highlights)
            st.image(img_bytes, use_container_width=True)
        
        with col2:
            st.subheader(f"🔍 Found {len(matches)} Potential PII Items")
            
            if matches:
                by_type = {}
                for i, m in enumerate(matches):
                    t = m["type"]
                    if t not in by_type:
                        by_type[t] = []
                    by_type[t].append((i, m))
                
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
                
                for pii_type, items in by_type.items():
                    # Mark premium patterns
                    is_premium_pattern = pii_type in PREMIUM_PATTERNS
                    label = f"**{pii_type}** ({len(items)} found)"
                    if is_premium_pattern:
                        label += " ⭐"
                    
                    with st.expander(label, expanded=True):
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
                
                selected_items = [matches[i] for i, sel in st.session_state.selected.items() if sel]
                
                if st.button(f"🔒 Redact {len(selected_items)} Selected Items", type="primary", disabled=len(selected_items)==0):
                    with st.spinner("Applying redactions..."):
                        redacted_pdf = redact_pdf(pdf_bytes, selected_items)
                        st.session_state.redacted_pdf = redacted_pdf
                        st.success(f"✅ Redacted {len(selected_items)} items!")
                
                if "redacted_pdf" in st.session_state:
                    st.download_button(
                        label="⬇️ Download Redacted PDF",
                        data=st.session_state.redacted_pdf,
                        file_name=f"redacted_{uploaded_file.name}",
                        mime="application/pdf"
                    )
            else:
                st.info("No sensitive information detected.")
            
            # Manual redaction
            st.divider()
            st.subheader("✏️ Manual Redaction")
            custom_text = st.text_input("Enter text to redact:", placeholder="Type exact text to find and redact...")
            
            if custom_text and st.button("Add to Redaction List"):
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                found = False
                for page_num_search, page in enumerate(doc):
                    rects = page.search_for(custom_text)
                    if rects:
                        new_match = {
                            "type": "Manual",
                            "text": custom_text,
                            "page": page_num_search + 1,
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
        # Instructions when no file uploaded
        st.markdown("""
        ### How it works:
        
        1. **Upload** a PDF document
        2. **Review** automatically detected sensitive information
        3. **Select** which items to redact
        4. **Download** your redacted PDF
        
        ---
        
        ### What we detect:
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Free Plan:**
            - 🔢 Social Security Numbers
            - 📅 Dates of Birth
            - 📞 Phone Numbers
            - 📧 Email Addresses
            - 🪪 Driver's License Numbers
            - 🏦 Account Numbers
            """)
        with col2:
            st.markdown("""
            **Premium Plan:** ⭐
            - 🏠 Street Addresses
            - 📮 Zip Codes
            - 💳 Credit Card Numbers
            - 📄 Batch Processing
            - 🤖 AI Detection (coming soon)
            """)

# ============ APP ENTRY POINT ============

def main():
    # Check if user is logged in
    if "user" not in st.session_state:
        show_auth_page()
        st.stop()
    
    user = st.session_state.user
    
    # Create user record if needed
    create_user_record(user.id, user.email)
    
    # Get user tier
    tier = get_user_tier(user.id)
    is_premium = tier == "premium"
    
    # Show main app
    show_main_app(user, is_premium)

if __name__ == "__main__":
    main()
