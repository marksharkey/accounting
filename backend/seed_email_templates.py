#!/usr/bin/env python3
"""
Seed default email templates into the database.
"""

from database import SessionLocal
from models import EmailTemplate, EmailTemplateType

# Default templates with HTML content
DEFAULT_TEMPLATES = {
    EmailTemplateType.new_invoice: {
        "subject": "Invoice {invoice_number} from {company_name}",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>Thank you for your business. Please find your invoice attached:</p>

<p>
  <strong>Invoice Number:</strong> {invoice_number}<br>
  <strong>Due Date:</strong> {due_date}<br>
  <strong>Amount Due:</strong> {amount_due}
</p>

<p>Please remit payment by the due date. Thank you!</p>

<p>Best regards,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.reminder_invoice: {
        "subject": "Payment Reminder: Invoice {invoice_number} is Due",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>This is a friendly reminder that payment for the following invoice is due:</p>

<p>
  <strong>Invoice Number:</strong> {invoice_number}<br>
  <strong>Due Date:</strong> {due_date}<br>
  <strong>Amount Due:</strong> {amount_due}
</p>

<p>Please arrange payment at your earliest convenience. If you have already paid, please disregard this notice.</p>

<p>Thank you!<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.invoice_past_due: {
        "subject": "Past Due Notice: Invoice {invoice_number}",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>We are writing to inform you that the following invoice is now past due:</p>

<p>
  <strong>Invoice Number:</strong> {invoice_number}<br>
  <strong>Due Date:</strong> {due_date}<br>
  <strong>Amount Due:</strong> {amount_due}
</p>

<p>Please arrange payment immediately. If you have questions regarding this invoice, please contact us right away.</p>

<p>Thank you,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.suspension_invoice: {
        "subject": "Account Suspension Warning - Immediate Action Required",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>This is a final notice that your account is subject to suspension due to unpaid invoices.</p>

<p>
  <strong>Current Balance Due:</strong> {amount_due}
</p>

<p>Please arrange payment immediately to prevent account suspension and disruption of services. Contact us if you have any questions or need to discuss payment arrangements.</p>

<p>Sincerely,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.cancellation_invoice: {
        "subject": "Account Cancellation Notice",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>Your account has been cancelled due to non-payment of outstanding invoices.</p>

<p>
  <strong>Outstanding Balance:</strong> {amount_due}
</p>

<p>If you believe this is in error or would like to discuss reinstatement of your account, please contact us immediately.</p>

<p>Thank you,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.paid_invoice: {
        "subject": "Payment Received - Thank You",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>Thank you for your payment! We have received your payment for the following invoice:</p>

<p>
  <strong>Invoice Number:</strong> {invoice_number}<br>
  <strong>Payment Amount:</strong> {payment_amount}<br>
  <strong>Date Paid:</strong> {payment_date}
</p>

<p>Your account is now up to date. We appreciate your prompt payment.</p>

<p>Best regards,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.credit_memo_issued: {
        "subject": "Credit Memo {memo_number} from {company_name}",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>A credit memo has been issued to your account:</p>

<p>
  <strong>Memo Number:</strong> {memo_number}<br>
  <strong>Credit Amount:</strong> {credit_amount}<br>
  <strong>Reason:</strong> {reason}
</p>

<p>This credit has been applied to your account. Please see the attached memo for details.</p>

<p>Thank you,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.payment_failed: {
        "subject": "Payment Failed - Action Required",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>We attempted to process a payment from your account but the transaction was declined.</p>

<p>
  <strong>Invoice Number:</strong> {invoice_number}<br>
  <strong>Amount Attempted:</strong> {amount_due}
</p>

<p>Please update your payment information or contact us to arrange alternate payment. If this issue is not resolved, your account may be subject to suspension.</p>

<p>Thank you,<br>
{company_name}</p>
</body>
</html>"""
    },
    EmailTemplateType.default: {
        "subject": "Important Account Update",
        "body": """<html>
<body>
<p>Hi {client_name},</p>

<p>This is an important message regarding your account.</p>

<p>Please contact us if you have any questions.</p>

<p>Thank you,<br>
{company_name}</p>
</body>
</html>"""
    }
}


def seed_templates():
    """Seed default email templates into database."""
    db = SessionLocal()

    try:
        # Check if templates already exist
        existing_count = db.query(EmailTemplate).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing templates. Skipping seed.")
            return

        # Insert default templates
        for template_type, content in DEFAULT_TEMPLATES.items():
            template = EmailTemplate(
                template_type=template_type,
                subject=content["subject"],
                body=content["body"],
                is_active=True
            )
            db.add(template)

        db.commit()
        print(f"✓ Seeded {len(DEFAULT_TEMPLATES)} default email templates")

    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding templates: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_templates()
