# PDF Redactor

A web app for automatically detecting and redacting sensitive information from PDF documents. Features a free tier with basic PII detection and a premium tier with advanced features.

## Features

### Free Tier
- Social Security Numbers (full, partial, last 4)
- Dates of Birth
- Phone Numbers
- Email Addresses
- Driver's License Numbers
- Account Numbers

### Premium Tier ($9/month)
- Everything in Free, plus:
- Street Address detection
- Zip Code detection
- Credit Card detection
- Batch processing (coming soon)
- AI-powered detection (coming soon)

## Live Demo

Try it at: [pdf-redactor-awesome.streamlit.app](https://pdf-redactor-awesome.streamlit.app)

## Setup (Self-Hosting)

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Go to SQL Editor and run the contents of `supabase_setup.sql`
3. Go to Settings → API and copy your URL and anon/public key

### 2. Create Stripe Account

1. Go to [stripe.com](https://stripe.com) and create an account
2. Create a Product (e.g., "PDF Redactor Premium")
3. Create a Price ($9/month recurring)
4. Copy your Secret Key and Price ID

### 3. Configure Secrets

For local development, create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_PRICE_ID = "price_..."
APP_URL = "http://localhost:8501"
```

For Streamlit Cloud, add these in the app settings under "Secrets".

### 4. Set Up Stripe Webhook (for subscription updates)

1. In Stripe Dashboard, go to Developers → Webhooks
2. Add endpoint: `https://your-app.streamlit.app/webhook` (or use a separate webhook handler)
3. Select events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

Note: Streamlit doesn't natively handle webhooks. For production, you'll need a small backend (e.g., Supabase Edge Function) to handle Stripe webhooks and update user tiers.

### 5. Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 6. Deploy to Streamlit Cloud

1. Push to GitHub
2. Connect repo to [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in app settings
4. Deploy

## Tech Stack

- **Frontend/App:** Streamlit
- **PDF Processing:** PyMuPDF
- **Auth & Database:** Supabase
- **Payments:** Stripe
