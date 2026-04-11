import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from config import get_settings

settings = get_settings()

# Setup Jinja2
template_dir = os.path.join(os.path.dirname(__file__), '..', 'email_templates')
env = Environment(loader=FileSystemLoader(template_dir))


async def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: dict,
    to_name: str = None
):
    """Send email with Jinja2 template rendering"""
    if not settings.smtp_host or not settings.smtp_user:
        print(f"Email not configured. Skipping: {subject} to {to_email}")
        return False

    try:
        # Render template
        template = env.get_template(template_name)
        html_content = template.render(**context)

        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email

        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))

        # Send via SMTP
        async with aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port
        ) as smtp:
            await smtp.login(settings.smtp_user, settings.smtp_password)
            await smtp.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


async def send_invoice_email(invoice, client):
    """Send invoice email"""
    return await send_email(
        to_email=client.email,
        subject=f"Invoice {invoice.invoice_number} from PrecisionPros",
        template_name="invoice.html",
        context={
            "client_name": client.company_name,
            "invoice_number": invoice.invoice_number,
            "total": f"${invoice.total:.2f}",
            "date": datetime.now().strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )


async def send_receipt_email(payment, invoice, client):
    """Send payment receipt email"""
    return await send_email(
        to_email=client.email,
        subject=f"Payment Receipt for Invoice {invoice.invoice_number}",
        template_name="receipt.html",
        context={
            "client_name": client.company_name,
            "invoice_number": invoice.invoice_number,
            "amount": f"${payment.amount:.2f}",
            "date": datetime.now().strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )


async def send_payment_reminder_email(invoice, client):
    """Send payment reminder email"""
    return await send_email(
        to_email=client.email,
        subject=f"Payment Reminder: Invoice {invoice.invoice_number} is Due",
        template_name="payment_reminder.html",
        context={
            "client_name": client.company_name,
            "invoice_number": invoice.invoice_number,
            "balance_due": f"${invoice.balance_due:.2f}",
            "due_date": invoice.due_date.strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )


async def send_late_fee_notice_email(invoice, client):
    """Send late fee notice email"""
    return await send_email(
        to_email=client.email,
        subject=f"Late Fee Applied to Invoice {invoice.invoice_number}",
        template_name="late_fee_notice.html",
        context={
            "client_name": client.company_name,
            "invoice_number": invoice.invoice_number,
            "late_fee": f"${invoice.late_fee_amount:.2f}",
            "balance_due": f"${invoice.balance_due:.2f}",
            "date": datetime.now().strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )


async def send_suspension_warning_email(client):
    """Send account suspension warning email"""
    return await send_email(
        to_email=client.email,
        subject="Account Suspension Warning - Immediate Action Required",
        template_name="suspension_warning.html",
        context={
            "client_name": client.company_name,
            "date": datetime.now().strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )


async def send_deletion_warning_email(client):
    """Send account deletion warning email"""
    return await send_email(
        to_email=client.email,
        subject="Final Notice - Account Deletion Pending",
        template_name="deletion_warning.html",
        context={
            "client_name": client.company_name,
            "date": datetime.now().strftime("%B %d, %Y"),
        },
        to_name=client.company_name,
    )
