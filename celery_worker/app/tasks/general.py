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
def send_email(previous_result: dict = None, recipient: str = None, subject: str = None, body: str = None):
    """
    A flexible email task that can be used standalone or as part of a chain.
    - If `previous_result` is provided, it will be used to format the email body.
    - If `previous_result` is NOT provided, the direct `body` argument will be used.
    """
    email_body = None

    # --- NEW: Logic to handle both chained and standalone calls ---
    if previous_result and isinstance(previous_result, dict):
        print("--- [TASK: send_email] Running as part of a chain. Formatting previous result. ---")
        # This is a chained task. Format the body from the previous result.
        scraped_data = previous_result.get("scraped_data", [])
        if not scraped_data:
            email_body = "The previous scraping task ran but found no data."
        else:
            email_body = "Here are the results from the web scrape:\n\n"
            email_body += "\n".join(f"- {item}" for item in scraped_data)
    else:
        print("--- [TASK: send_email] Running as a standalone task. ---")
        # This is a standalone task. Use the 'body' argument directly.
        email_body = body
    # --- END NEW ---

    # --- Validation ---
    if not recipient:
        raise ValueError("Email recipient is missing.")
    if not subject:
        raise ValueError("Email subject is missing.")
    if not email_body:
        email_body = subject # Fallback to subject if body is empty
        # raise ValueError("Email body is empty or could not be generated.")

    # --- Email Sending Logic (largely unchanged) ---
    sender_email = os.environ.get("EMAIL_HOST_USER")
    sender_password = os.environ.get("EMAIL_HOST_PASSWORD")
    sender_name = os.environ.get("EMAIL_SENDER_NAME", sender_email)

    if not all([sender_email, sender_password]):
        raise ValueError("Email credentials not configured in environment variables.")

    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(email_body)

    print(f"--- [TASK: send_email] Attempting to send email to '{recipient}' ---")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)

        success_message = f"Successfully sent email to {recipient}"
        print(f"--- [TASK: send_email] {success_message} ---")
        return success_message

    except Exception as e:
        error_message = f"Failed to send email: {e}"
        print(f"!!! [TASK: send_email] {error_message} !!!")
        raise e



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