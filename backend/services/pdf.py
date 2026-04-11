from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from io import BytesIO
import os
from datetime import datetime
from decimal import Decimal
import re
from sqlalchemy.orm import Session


# Setup Jinja2
template_dir = os.path.join(os.path.dirname(__file__), '..', 'pdf_templates')
env = Environment(loader=FileSystemLoader(template_dir))


def format_phone(phone):
    """Format phone number to (XXX) XXX-XXXX"""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def generate_invoice_pdf(invoice, client, db: Session = None):
    """Generate PDF for an invoice using WeasyPrint"""
    try:
        # Get company info from database, fallback to defaults if not set
        company_info = {
            'name': 'PrecisionPros',
            'address1': '6543 East Omega Street',
            'address2': 'Mesa, AZ 85215',
            'phone': '480-329-6176',
            'email': 'billing@precisionpros.com',
        }

        if db:
            import models
            company = db.query(models.CompanyInfo).first()
            if company:
                company_info['name'] = company.company_name
                company_info['address1'] = company.address_line1 or ''
                company_info['address2'] = (
                    f"{company.city or ''}, {company.state or ''} {company.zip_code or ''}".strip()
                    if company.city or company.state or company.zip_code else ''
                )
                if company.address_line2:
                    company_info['address1'] = f"{company_info['address1']}\n{company.address_line2}".strip()
                company_info['phone'] = company.phone or company_info['phone']
                company_info['email'] = company.email or company_info['email']

        # Prepare line items
        line_items = []
        for item in invoice.line_items:
            line_items.append({
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_amount': float(item.unit_amount),
                'amount': float(item.amount),
                'is_prorated': item.is_prorated,
                'prorate_note': item.prorate_note,
            })

        # Format numbers
        subtotal = float(invoice.subtotal)
        amount_paid = float(invoice.amount_paid) if invoice.amount_paid else 0.0
        late_fee = float(invoice.late_fee_amount) if invoice.late_fee_amount else 0.0
        total = float(invoice.total)
        balance_due = float(invoice.balance_due)
        previous_balance = float(invoice.previous_balance) if invoice.previous_balance else 0.0

        # Calculate account summary variables
        payments_on_account = sum(float(p.amount) for p in invoice.payments) if invoice.payments else 0.0
        total_amount_due = previous_balance + total - payments_on_account
        show_account_summary = previous_balance != 0.0 or payments_on_account != 0.0

        # Render template
        template = env.get_template('invoice.html')
        html_content = template.render(
            # Company info
            company_name=company_info['name'],
            company_address1=company_info['address1'],
            company_address2=company_info['address2'],
            company_phone=company_info['phone'],
            company_email=company_info['email'],

            # Invoice details
            invoice_number=invoice.invoice_number,
            created_date=invoice.created_date.strftime("%b %d, %Y"),
            due_date=invoice.due_date.strftime("%b %d, %Y"),
            status=invoice.status.value,
            status_display=invoice.status.value.replace('_', ' ').title(),

            # Client info
            client_name=client.company_name,
            contact_name=client.contact_name or '',
            email=client.email,
            phone=format_phone(client.phone) if client.phone else '',
            address_line1=client.address_line1 or '',
            address_line2=client.address_line2 or '',
            city=client.city or '',
            state=client.state or '',
            zip_code=client.zip_code or '',

            # Line items and totals
            line_items=line_items,
            subtotal=f"${subtotal:.2f}",
            amount_paid=f"${amount_paid:.2f}",
            late_fee=f"${late_fee:.2f}" if late_fee > 0 else None,
            total=f"${total:.2f}",
            balance_due=f"${balance_due:.2f}",
            notes=invoice.notes or '',

            # Account summary
            previous_balance=f"${previous_balance:.2f}",
            payments_on_account=f"${payments_on_account:.2f}",
            total_amount_due=f"${total_amount_due:.2f}",
            show_account_summary=show_account_summary,
        )

        # Convert HTML to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        return BytesIO(pdf_bytes)

    except Exception as e:
        print(f"Error generating invoice PDF: {e}")
        raise
