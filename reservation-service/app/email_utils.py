import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging

logger = logging.getLogger(__name__)

def send_email(to_email, subject, body, attachment=None, attachment_name=None):
    """Send an email using SMTP with an optional attachment."""
    try:
        email_host = os.getenv('EMAIL_HOST')
        email_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_host, email_port, email_username, email_password, email_from]):
            logger.error("Email configuration is incomplete.")
            return False

        # Set up the email
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach the file if provided
        if attachment and attachment_name:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
            msg.attach(part)

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(email_host, email_port) as server:
            server.starttls()
            server.login(email_username, email_password)
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
