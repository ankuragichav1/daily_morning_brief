"""
email_sender.py
Sends HTML report via Gmail using app password (no paid service needed).
Setup: https://myaccount.google.com/apppasswords
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_report(subject: str, html_body: str) -> bool:
    """
    Send HTML email via Gmail SMTP.
    Required env vars:
      GMAIL_USER     — your Gmail address (e.g. you@gmail.com)
      GMAIL_APP_PASS — 16-char Gmail App Password (NOT your regular password)
      REPORT_TO      — recipient email (can be same as GMAIL_USER)
    """
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASS")
    report_to  = os.environ.get("REPORT_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        raise ValueError("GMAIL_USER and GMAIL_APP_PASS environment variables must be set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Portfolio Brief <{gmail_user}>"
    msg["To"]      = report_to

    # Attach HTML part
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, report_to, msg.as_string())
        logger.info(f"✅ Report sent to {report_to}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail auth failed — check GMAIL_USER and GMAIL_APP_PASS")
        raise
    except Exception as e:
        logger.error(f"❌ Email send failed: {e}")
        raise
