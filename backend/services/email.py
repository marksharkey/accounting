import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from config import get_settings
from io import BytesIO
from database import SessionLocal
from models import EmailTemplate, EmailTemplateType

settings = get_settings()


def _get_email_recipient(to_email: str, to_name: str = None) -> tuple[str, str]:
    """
    Get the actual recipient email address, redirecting to dev email if in dev mode.
    Returns (actual_to_email, actual_to_name)
    """
    if settings.dev_mode:
        if to_email != settings.dev_email:  # Only log if not already dev email
            print(f"[DEV MODE] Redirecting email from '{to_email}' to '{settings.dev_email}'")
        return settings.dev_email, "Developer"
    return to_email, to_name


async def _get_template(template_type: EmailTemplateType):
    """Get a template from database, with fallback to default template."""
    db = SessionLocal()
    try:
        template = db.query(EmailTemplate).filter(
            EmailTemplate.template_type == template_type
        ).first()

        if template and template.is_active:
            return template

        # Fall back to default template if not found or inactive
        default = db.query(EmailTemplate).filter(
            EmailTemplate.template_type == EmailTemplateType.default
        ).first()

        return default if default else None
    finally:
        db.close()


def _render_template_string(template_string: str, context: dict) -> str:
    """Render a template string with {variable} syntax using context variables."""
    if not template_string:
        return ""

    try:
        # Use Python's str.format() which supports {variable} syntax
        return template_string.format(**context)
    except KeyError as e:
        # If a variable is missing, return the original string with missing vars left as-is
        print(f"Warning: Missing template variable: {e}")
        return template_string
    except Exception as e:
        print(f"Error rendering template: {e}")
        return template_string  # Return unrendered on error


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    to_name: str = None,
    attachment_bytes: BytesIO = None,
    attachment_filename: str = None
):
    """Send an email with HTML body and optional attachment."""
    if not settings.smtp_host or not settings.smtp_user:
        print(f"Email not configured. Skipping: {subject} to {to_email}")
        return False

    # Redirect to dev email if in dev mode
    to_email, to_name = _get_email_recipient(to_email, to_name)

    try:
        # Create email
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email

        # Attach HTML content
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(html_body, 'html'))
        msg.attach(msg_alternative)

        # Attach file if provided
        if attachment_bytes and attachment_filename:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_bytes.getvalue())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {attachment_filename}')
            msg.attach(part)

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


async def send_template_email(
    to_email: str,
    template_type: EmailTemplateType,
    context: dict,
    to_name: str = None,
    attachment_bytes: BytesIO = None,
    attachment_filename: str = None
):
    """
    Send an email using a template from the database.

    Args:
        to_email: Recipient email address
        template_type: EmailTemplateType enum value
        context: Dictionary of variables to render in template
        to_name: Recipient name (optional)
        attachment_bytes: File content to attach (optional)
        attachment_filename: Name of attachment (optional)
    """
    if not settings.smtp_host or not settings.smtp_user:
        print(f"Email not configured. Skipping template: {template_type.value} to {to_email}")
        return False

    try:
        template = await _get_template(template_type)

        if not template:
            print(f"No template found for type: {template_type.value}")
            return False

        # Render subject and body with context variables
        subject = _render_template_string(template.subject, context)
        html_body = _render_template_string(template.body, context)

        return await send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            to_name=to_name,
            attachment_bytes=attachment_bytes,
            attachment_filename=attachment_filename
        )
    except Exception as e:
        print(f"Error sending template email: {e}")
        return False


# ─────────────────────────────────────────────
# High-Level Email Functions (Invoice-Related)
# ─────────────────────────────────────────────

def _build_invoice_context(invoice, client):
    """Build template context for invoice emails."""
    company_name = getattr(settings, 'company_name', None) or "Our Company"
    return {
        "client_name": client.display_name,
        "invoice_number": invoice.invoice_number,
        "amount_due": f"${invoice.total:.2f}",
        "due_date": invoice.due_date.strftime("%B %d, %Y"),
        "company_name": company_name,
    }


async def send_new_invoice_email(invoice, client):
    """Send new invoice notification."""
    return await send_invoice_email_with_type(invoice, client, EmailTemplateType.new_invoice)


async def send_invoice_email_with_type(invoice, client, template_type=EmailTemplateType.new_invoice):
    """Send invoice email using specified template type."""
    try:
        from services.pdf import generate_invoice_pdf
        # Note: db not passed here - email attachments use default company info
        # For real company info, use the PDF download endpoints in the routers
        pdf_bytes = generate_invoice_pdf(invoice, client)

        return await send_template_email(
            to_email=client.email,
            template_type=template_type,
            context=_build_invoice_context(invoice, client),
            to_name=client.display_name,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{invoice.invoice_number}.pdf"
        )
    except Exception as e:
        print(f"Error sending invoice email with PDF: {e}")
        # Fall back to email without attachment
        return await send_template_email(
            to_email=client.email,
            template_type=template_type,
            context=_build_invoice_context(invoice, client),
            to_name=client.display_name,
        )


async def send_reminder_email(invoice, client):
    """Send payment reminder."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.reminder_invoice,
        context={
            "client_name": client.display_name,
            "invoice_number": invoice.invoice_number,
            "balance_due": f"${invoice.balance_due:.2f}",
            "due_date": invoice.due_date.strftime("%B %d, %Y"),
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_past_due_email(invoice, client):
    """Send past due notice."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.invoice_past_due,
        context={
            "client_name": client.display_name,
            "invoice_number": invoice.invoice_number,
            "balance_due": f"${invoice.balance_due:.2f}",
            "due_date": invoice.due_date.strftime("%B %d, %Y"),
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_suspension_warning_email(client):
    """Send account suspension warning."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.suspension_invoice,
        context={
            "client_name": client.display_name,
            "amount_due": f"${client.account_balance:.2f}",
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_cancellation_email(client):
    """Send account cancellation notice."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.cancellation_invoice,
        context={
            "client_name": client.display_name,
            "amount_due": f"${client.account_balance:.2f}",
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_payment_received_email(payment, invoice, client):
    """Send payment received confirmation."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.paid_invoice,
        context={
            "client_name": client.display_name,
            "invoice_number": invoice.invoice_number,
            "payment_amount": f"${payment.amount:.2f}",
            "payment_date": datetime.utcnow().strftime("%B %d, %Y"),
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_credit_memo_email(memo, client):
    """Send credit memo notification."""
    try:
        from services.pdf import generate_credit_memo_pdf
        # Note: db not passed here - email attachments use default company info
        # For real company info, use the PDF download endpoints in the routers
        pdf_bytes = generate_credit_memo_pdf(memo, client)

        return await send_template_email(
            to_email=client.email,
            template_type=EmailTemplateType.credit_memo_issued,
            context={
                "client_name": client.display_name,
                "memo_number": memo.memo_number,
                "credit_amount": f"${memo.total:.2f}",
                "reason": memo.reason or "",
                "company_name": settings.company_name or "Our Company",
            },
            to_name=client.display_name,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"credit-memo-{memo.memo_number}.pdf"
        )
    except Exception as e:
        print(f"Error sending credit memo email with PDF: {e}")
        # Fall back to email without attachment
        return await send_template_email(
            to_email=client.email,
            template_type=EmailTemplateType.credit_memo_issued,
            context={
                "client_name": client.display_name,
                "memo_number": memo.memo_number,
                "credit_amount": f"${memo.total:.2f}",
                "reason": memo.reason or "",
                "company_name": settings.company_name or "Our Company",
            },
            to_name=client.display_name,
        )


async def send_payment_failed_email(client, invoice=None, amount_due=None):
    """Send payment failure notification (e.g., CC declined)."""
    context = {
        "client_name": client.display_name,
        "company_name": settings.company_name or "Our Company",
    }

    if invoice:
        context["invoice_number"] = invoice.invoice_number
        context["amount_due"] = f"${invoice.balance_due:.2f}"
    elif amount_due:
        context["amount_due"] = f"${amount_due:.2f}"

    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.payment_failed,
        context=context,
        to_name=client.display_name,
    )


# ─────────────────────────────────────────────
# Backward Compatibility Aliases
# ─────────────────────────────────────────────

async def send_invoice_email(invoice, client):
    """Backward compatibility alias for send_new_invoice_email."""
    return await send_new_invoice_email(invoice, client)


async def send_receipt_email(payment, invoice, client):
    """Backward compatibility alias for send_payment_received_email."""
    return await send_payment_received_email(payment, invoice, client)


async def send_cc_declined_email(client):
    """Backward compatibility alias for send_payment_failed_email."""
    return await send_payment_failed_email(client)


async def send_late_fee_notice_email(invoice, client):
    """Send late fee notice. Alias that uses past_due template."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.invoice_past_due,
        context={
            "client_name": client.display_name,
            "invoice_number": invoice.invoice_number,
            "balance_due": f"${invoice.balance_due:.2f}",
            "due_date": invoice.due_date.strftime("%B %d, %Y"),
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


async def send_deletion_warning_email(client):
    """Send account deletion warning. Alias that uses cancellation template."""
    return await send_template_email(
        to_email=client.email,
        template_type=EmailTemplateType.cancellation_invoice,
        context={
            "client_name": client.display_name,
            "amount_due": f"${client.account_balance:.2f}",
            "company_name": settings.company_name or "Our Company",
        },
        to_name=client.display_name,
    )


# ─────────────────────────────────────────────
# Account Recovery Emails
# ─────────────────────────────────────────────

async def send_forgot_username_email(user):
    """Send username reminder to user."""
    subject = "Your PrecisionPros Username"
    html_body = f"""
    <p>Hi {user.full_name},</p>
    <p>Your username is: <strong>{user.username}</strong></p>
    <p>If you did not request this, you can ignore this email.</p>
    """
    return await send_email(
        to_email=user.email,
        subject=subject,
        html_body=html_body,
        to_name=user.full_name,
    )


async def send_password_reset_email(user, token: str):
    """Send password reset link to user."""
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    subject = "Reset Your PrecisionPros Password"
    html_body = f"""
    <p>Hi {user.full_name},</p>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>If you did not request this, ignore this email.</p>
    """
    return await send_email(
        to_email=user.email,
        subject=subject,
        html_body=html_body,
        to_name=user.full_name,
    )
