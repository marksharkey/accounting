#!/usr/bin/env python3
"""
Test suite for Milestone 3: Email template sending logic
"""

import pytest
import asyncio
from database import SessionLocal
from models import EmailTemplate, EmailTemplateType
from services.email import (
    _render_template_string,
    _get_template,
)


@pytest.fixture
def db():
    """Get database session for tests."""
    db = SessionLocal()
    yield db
    db.close()


class TestTemplateRendering:
    """Test template string rendering with variables."""

    def test_simple_variable_rendering(self):
        """Test rendering simple variables."""
        template = "Hello {name}, your amount is {amount}"
        context = {"name": "John", "amount": "$100.00"}

        result = _render_template_string(template, context)
        assert result == "Hello John, your amount is $100.00"

    def test_html_template_rendering(self):
        """Test rendering HTML templates with variables."""
        template = "<html><body><p>Invoice {number} for {client}</p></body></html>"
        context = {"number": "INV-001", "client": "Acme Corp"}

        result = _render_template_string(template, context)
        assert "INV-001" in result
        assert "Acme Corp" in result
        assert "<html>" in result

    def test_missing_variable(self):
        """Test rendering with missing variable (returns unrendered on error)."""
        template = "Hello {name}, your invoice {invoice_number}"
        context = {"name": "John"}  # invoice_number is missing

        result = _render_template_string(template, context)
        # When a variable is missing, the template is returned unrendered
        assert result == template

    def test_empty_template(self):
        """Test rendering empty template."""
        result = _render_template_string("", {})
        assert result == ""

    def test_template_without_variables(self):
        """Test rendering template with no variables."""
        template = "<html><body>Static content</body></html>"
        result = _render_template_string(template, {})
        assert result == template

    def test_template_rendering_with_special_characters(self):
        """Test rendering templates with special HTML characters."""
        template = "<p>Invoice for {client_name} - Amount: {amount}</p>"
        context = {
            "client_name": "Smith & Jones <Inc>",
            "amount": "$1,000.00"
        }

        result = _render_template_string(template, context)
        assert "Smith & Jones <Inc>" in result
        assert "$1,000.00" in result

    def test_template_with_multiple_variable_occurrences(self):
        """Test rendering template where variable appears multiple times."""
        template = """
    <html>
    <body>
    <p>Hello {client_name},</p>
    <p>Invoice for {client_name} has been created.</p>
    <p>Please contact {client_name} if you have questions.</p>
    </body>
    </html>
    """
        context = {"client_name": "Acme Corp"}

        result = _render_template_string(template, context)
        # All three instances should be replaced
        assert result.count("Acme Corp") == 3


def test_get_template_from_database(db):
    """Test retrieving template from database."""
    template = asyncio.run(_get_template(EmailTemplateType.new_invoice))

    assert template is not None
    assert template.template_type == EmailTemplateType.new_invoice
    assert template.subject is not None
    assert template.body is not None


def test_get_inactive_template_falls_back_to_default(db):
    """Test that inactive templates fall back to default."""
    # Deactivate new_invoice template
    new_invoice = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == EmailTemplateType.new_invoice
    ).first()
    new_invoice.is_active = False
    db.commit()

    # Should get default template
    result = asyncio.run(_get_template(EmailTemplateType.new_invoice))
    assert result is not None
    assert result.template_type == EmailTemplateType.default

    # Restore
    new_invoice.is_active = True
    db.commit()


def test_template_context_substitution_in_database_templates(db):
    """Test that database templates can be rendered with context variables."""
    # Get a real template from the database
    template = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == EmailTemplateType.new_invoice
    ).first()

    context = {
        "client_name": "Acme Corp",
        "invoice_number": "INV-2026-001",
        "amount_due": "$2,500.00",
        "due_date": "May 15, 2026",
        "company_name": "PrecisionPros",
    }

    # Render the subject
    rendered_subject = _render_template_string(template.subject, context)
    assert "INV-2026-001" in rendered_subject
    assert "PrecisionPros" in rendered_subject

    # Render the body
    rendered_body = _render_template_string(template.body, context)
    assert "Acme Corp" in rendered_body
    assert "INV-2026-001" in rendered_body
    assert "$2,500.00" in rendered_body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
