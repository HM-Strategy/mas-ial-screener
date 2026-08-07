import os
import base64
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def send_notification_email(to_emails: list[str], pdf_bytes: bytes, new_count: int, match_count: int) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY not set.")
        return False

    from_email = os.getenv("FROM_EMAIL")
    if not from_email:
        logger.error("FROM_EMAIL not set.")
        return False

    if not to_emails:
        logger.error("No recipients provided.")
        return False

    run_date = datetime.now().strftime("%d %b %Y")

    if match_count > 0:
        subject = f"URGENT: MAS Alert — {run_date}: New Entries & Client Matches Found"
    else:
        subject = f"MAS Alert — {run_date}: {new_count} New Entries on Investor Alert List"

    body = (
        f"This is an automated notification from the HM Strategy MAS Investor Alert List screening agent.\n\n"
        f"The Investor Alert List was screened and {new_count} new entr{'y' if new_count == 1 else 'ies'} "
        f"found for {run_date}.\n"
        f"Client matches found: {match_count}\n\n"
        f"Full details for the day are in the attached PDF (MAS_Alert_Notification.pdf)."
    )

    payload = {
        "from": from_email,
        "to": to_emails,
        "subject": subject,
        "text": body,
        "attachments": [
            {
                "filename": "MAS_Alert_Notification.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(RESEND_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            logger.info("Email sent to %d recipient(s).", len(to_emails))
            return True
        logger.error("Resend API error %s: %s", resp.status_code, resp.text[:500])
        return False
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
