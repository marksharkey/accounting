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


def generate_credit_memo_pdf(memo, client, db: Session = None):
    """Generate PDF for a credit memo using WeasyPrint"""
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
        for item in memo.line_items:
            line_items.append({
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_amount': float(item.unit_amount),
                'amount': float(item.amount),
            })

        # Format numbers
        total = float(memo.total)

        # Render template using a simple HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ margin-bottom: 40px; }}
                .header h1 {{ color: #27ae60; margin: 0; }}
                .company-info {{ color: #666; font-size: 12px; margin-bottom: 30px; }}
                .section-title {{ color: #2c3e50; font-weight: bold; margin-top: 20px; margin-bottom: 10px; }}
                .client-info {{ margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background-color: #f5f5f5; padding: 10px; text-align: left; border-bottom: 2px solid #ddd; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                .amount-col {{ text-align: right; }}
                .total-section {{ margin-top: 20px; text-align: right; }}
                .total-amount {{ font-size: 18px; font-weight: bold; color: #27ae60; }}
                .memo-info {{ margin: 20px 0; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Credit Memo {{ memo_number }}</h1>
                <div class="company-info">
                    <p><strong>{{ company_name }}</strong></p>
                    {% if company_address1 %}<p>{{ company_address1 }}</p>{% endif %}
                    {% if company_address2 %}<p>{{ company_address2 }}</p>{% endif %}
                    {% if company_phone %}<p>{{ company_phone }}</p>{% endif %}
                    {% if company_email %}<p>{{ company_email }}</p>{% endif %}
                </div>
            </div>

            <div class="memo-info">
                <p><strong>Date:</strong> {{ created_date }}</p>
            </div>

            <div class="section-title">Bill To</div>
            <div class="client-info">
                <p><strong>{{ client_name }}</strong></p>
                {% if contact_name %}<p>{{ contact_name }}</p>{% endif %}
                {% if email %}<p>{{ email }}</p>{% endif %}
                {% if phone %}<p>{{ phone }}</p>{% endif %}
                {% if address_line1 %}<p>{{ address_line1 }}</p>{% endif %}
                {% if address_line2 %}<p>{{ address_line2 }}</p>{% endif %}
                {% if city %}<p>{{ city }}{% if state %}, {{ state }}{% endif %} {% if zip_code %}{{ zip_code }}{% endif %}</p>{% endif %}
            </div>

            <div class="section-title">Credit Items</div>
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th style="width: 80px;" class="amount-col">Qty</th>
                        <th style="width: 100px;" class="amount-col">Unit Amount</th>
                        <th style="width: 100px;" class="amount-col">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in line_items %}
                    <tr>
                        <td>{{ item.description }}</td>
                        <td class="amount-col">{{ "%.2f"|format(item.quantity) }}</td>
                        <td class="amount-col">${{ "%.2f"|format(item.unit_amount) }}</td>
                        <td class="amount-col"><strong>${{ "%.2f"|format(item.amount) }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <div class="total-section">
                <p><strong>Total Credit Amount:</strong> <span class="total-amount">${{ "%.2f"|format(total) }}</span></p>
            </div>

            {% if reason %}
            <div style="margin-top: 30px;">
                <div class="section-title">Reason</div>
                <p>{{ reason }}</p>
            </div>
            {% endif %}

            {% if notes %}
            <div style="margin-top: 20px;">
                <div class="section-title">Notes</div>
                <p>{{ notes }}</p>
            </div>
            {% endif %}
        </body>
        </html>
        """

        template = env.from_string(html_template)
        html_content = template.render(
            # Company info
            company_name=company_info['name'],
            company_address1=company_info['address1'],
            company_address2=company_info['address2'],
            company_phone=company_info['phone'],
            company_email=company_info['email'],

            # Memo details
            memo_number=memo.memo_number,
            created_date=memo.created_date.strftime("%b %d, %Y"),
            status=memo.status.value,
            status_display=memo.status.value.replace('_', ' ').title(),

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
            total=total,
            reason=memo.reason or '',
            notes=memo.notes or '',
        )

        # Convert HTML to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        return BytesIO(pdf_bytes)

    except Exception as e:
        print(f"Error generating credit memo PDF: {e}")
        raise


def generate_pl_pdf(data, company_info=None):
    """Generate PDF for a Profit & Loss statement using WeasyPrint"""
    try:
        # Set default company info
        company_details = {
            'name': 'PrecisionPros',
            'address1': '6543 East Omega Street',
            'address2': 'Mesa, AZ 85215',
            'phone': '480-329-6176',
            'email': 'billing@precisionpros.com',
        }

        # Override with provided company info
        if company_info:
            company_details['name'] = company_info.company_name
            company_details['address1'] = company_info.address_line1 or ''
            company_details['address2'] = (
                f"{company_info.city or ''}, {company_info.state or ''} {company_info.zip_code or ''}".strip()
                if company_info.city or company_info.state or company_info.zip_code else ''
            )
            if company_info.address_line2:
                company_details['address1'] = f"{company_details['address1']}\n{company_info.address_line2}".strip()
            company_details['phone'] = company_info.phone or company_details['phone']
            company_details['email'] = company_info.email or company_details['email']

        # Format dates
        from_date = data['from_date'].strftime("%b %d, %Y")
        to_date = data['to_date'].strftime("%b %d, %Y")
        now = datetime.now()
        generated_date = now.strftime("%b %d, %Y at %I:%M %p")

        # Render template
        template = env.get_template('profit_loss.html')
        html_content = template.render(
            company_name=company_details['name'],
            company_address1=company_details['address1'],
            company_address2=company_details['address2'],
            company_phone=company_details['phone'],
            company_email=company_details['email'],
            from_date=from_date,
            to_date=to_date,
            income=data['income'],
            total_income=data['total_income'],
            expenses=data['expenses'],
            total_expenses=data['total_expenses'],
            net_income=data['net_income'],
            net_income_formatted=f"${abs(data['net_income']):.2f}",
            is_profitable=data['net_income'] >= 0,
            generated_date=generated_date,
        )

        # Convert HTML to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes

    except Exception as e:
        print(f"Error generating P&L PDF: {e}")
        raise
