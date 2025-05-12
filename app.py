import os
import base64
import time
import pandas as pd
import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText

from streamlit_quill import st_quill  # ✅ Rich Text Editor

# ----------------------------
# Gmail API Authentication
# ----------------------------

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def gmail_authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # ✅ Use credentials from secrets.toml
            credentials = {
                "installed": {
                    "client_id": st.secrets.gmail["client_id"],
                    "project_id": st.secrets.gmail["project_id"],
                    "auth_uri": st.secrets.gmail["auth_uri"],
                    "token_uri": st.secrets.gmail["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets.gmail["auth_provider_x509_cert_url"],
                    "client_secret": st.secrets.gmail["client_secret"],
                    "redirect_uris": st.secrets.gmail["redirect_uris"]
                }
            }
            # Save to a temporary file
            with open("temp_credentials.json", "w") as f:
                import json
                json.dump(credentials, f)

            flow = InstalledAppFlow.from_client_secrets_file("temp_credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            os.remove("temp_credentials.json")  # clean up

        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# ----------------------------
# Create and Send Email
# ----------------------------

def create_message(to, subject, message_html):  # Changed to HTML
    message = MIMEText(message_html, "html")  # ✅ HTML for rich text
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email(service, to, subject, message_html):
    message = create_message(to, subject, message_html)
    return service.users().messages().send(userId="me", body=message).execute()

# ----------------------------
# Streamlit UI
# ----------------------------

st.set_page_config(page_title="Swift Email Sender", page_icon="📧")
st.title("📧 Swift Email Sender via Gmail")

uploaded_file = st.file_uploader("Upload CSV with emails (column: email)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if 'email' not in df.columns:
        st.error("CSV must contain a column named 'email'")
    else:
        st.dataframe(df)

        subject = st.text_input("Email Subject", "Load Details")

        # ✅ Rich Text Editor for email body
        st.subheader("Compose Email")  # acts like a label
        message_body = st_quill(html=True)

        if st.button("Send Emails"):
            with st.spinner("Sending emails..."):  # ✅ Loading spinner
                st.info("Authenticating Gmail... please wait.")
                service = gmail_authenticate()

                total = len(df)
                progress = st.progress(0)
                status = st.empty()

                for index, row in df.iterrows():
                    to = row['email']
                    try:
                        send_email(service, to, subject, message_body)
                        status.success(f"✅ Email sent to {to}")
                    except Exception as e:
                        status.error(f"❌ Failed to send to {to}: {e}")
                    time.sleep(5)
                    progress.progress((index + 1) / total)

                st.success("🎉 All emails processed.")
