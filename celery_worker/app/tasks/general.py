import time
from celery_app import celery_app

import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup


# The SMTP server and port for Gmail
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


@celery_app.task(name="send_email")
def send_email(recipient: str = None, subject: str = None, body: str = None, **kwargs):
    """
    Sends an email using Gmail's SMTP server and credentials from environment variables.
    Accepts body/content/message/text for flexibility.
    """
    # Normalize parameters
    email_body = body or kwargs.get("content") or kwargs.get("message") or kwargs.get("text")
    if not recipient:
        raise ValueError("Missing recipient email address.")
    if not subject:
        raise ValueError("Missing subject.")
    if not email_body:
        raise ValueError("Missing email body (expected 'body', 'content', 'message', or 'text').")

    sender_email = os.environ.get("EMAIL_HOST_USER")
    sender_password = os.environ.get("EMAIL_HOST_PASSWORD")
    sender_name = os.environ.get("EMAIL_SENDER_NAME", sender_email)

    print(" -----------pRINTING EMAIL AND PASSWORD---------------",sender_email, sender_password)


    if not all([sender_email, sender_password]):
        raise ValueError("Email credentials not configured in environment variables.")

    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(email_body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(f"✅ Email sent to {recipient}")
        return f"Successfully sent email to {recipient}"

    except Exception as e:
        print(f"❌ Email failed: {e}")
        raise



@celery_app.task(name="scrape_web", bind=True)
def scrape_web(self, url: str, selector: str):
    """
    Scrapes a webpage for elements matching a CSS selector.

    :param url: The URL to scrape.
    :param selector: The CSS selector to find elements (e.g., 'h2', '.titleline > a').
    """
    print(f"--- [TASK: scrape_web] Attempting to scrape URL: {url} with selector: '{selector}' ---")
    
    # Many websites block requests that don't have a valid User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # Set a timeout to prevent the task from hanging indefinitely
        response = requests.get(url, headers=headers, timeout=15)
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all elements that match the provided CSS selector
        elements = soup.select(selector)

        if not elements:
            message = f"Successfully scraped {url}, but found 0 elements matching selector '{selector}'."
            print(f"--- [TASK: scrape_web] {message} ---")
            return message

        # Extract the text from the found elements, stripping extra whitespace
        # and limiting the results to the first 20 to avoid huge outputs.
        results = [el.get_text(strip=True) for el in elements[:20]]

        success_message = f"Successfully scraped {url}. Found {len(elements)} element(s). Returning first {len(results)}."
        print(f"--- [TASK: scrape_web] {success_message} ---")
        print(f"Results: {results}")
        return {"scraped_data": results}

    except requests.exceptions.RequestException as e:
        error_message = f"Failed to scrape URL {url}. Network error: {e}"
        print(f"!!! [TASK: scrape_web] {error_message} !!!")
        # Retry the task after a delay (e.g., 5 minutes). Can be configured.
        raise self.retry(exc=e, countdown=300)

    except Exception as e:
        error_message = f"An unexpected error occurred during scraping: {e}"
        print(f"!!! [TASK: scrape_web] {error_message} !!!")
        raise e

@celery_app.task(name="call_api")
def call_api(endpoint: str, payload: dict):
    print(f"--- TASK: Calling API: {endpoint} ---")
    time.sleep(2)
    print("--- TASK: API call successful. ---")
    return f"API call to {endpoint} returned success"