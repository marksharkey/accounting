#!/usr/bin/env python3
"""
Test suite for Milestone 1: Email Template Database Schema
"""

import pytest
from database import SessionLocal
from models import EmailTemplate, EmailTemplateType


@pytest.fixture
def db():
    """Get database session for tests."""
    db = SessionLocal()
    yield db
    db.close()


def test_email_template_model_exists():
    """Test that EmailTemplate model exists and is properly defined."""
    assert EmailTemplate is not None
    assert hasattr(EmailTemplate, '__tablename__')
    assert EmailTemplate.__tablename__ == 'email_templates'


def test_email_template_enum_types():
    """Test that all required EmailTemplateType enums exist."""
    required_types = [
        'new_invoice',
        'reminder_invoice',
        'invoice_past_due',
        'suspension_invoice',
        'cancellation_invoice',
        'paid_invoice',
        'credit_memo_issued',
        'payment_failed',
        'default'
    ]

    for type_name in required_types:
        enum_val = EmailTemplateType[type_name]
        assert enum_val.value == type_name


def test_all_templates_seeded(db):
    """Test that all 9 default templates are in the database."""
    templates = db.query(EmailTemplate).all()
    assert len(templates) == 9, f"Expected 9 templates, got {len(templates)}"


def test_template_fields_populated(db):
    """Test that each template has required fields."""
    templates = db.query(EmailTemplate).all()

    for template in templates:
        assert template.id is not None
        assert template.template_type is not None
        assert template.subject is not None
        assert len(template.subject) > 0
        assert template.body is not None
        assert len(template.body) > 0
        assert template.is_active is True
        assert template.created_at is not None
        assert template.updated_at is not None


def test_template_unique_type(db):
    """Test that template_type is unique."""
    templates = db.query(EmailTemplate).all()
    types = [t.template_type for t in templates]
    assert len(types) == len(set(types)), "template_type values are not unique"


def test_query_template_by_type(db):
    """Test querying a template by type."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == EmailTemplateType.new_invoice
    ).first()

    assert template is not None
    assert template.template_type == EmailTemplateType.new_invoice
    assert "invoice" in template.subject.lower()


def test_template_variable_placeholders(db):
    """Test that templates contain expected variable placeholders."""
    expected_vars = {
        EmailTemplateType.new_invoice: ['{invoice_number}', '{client_name}', '{company_name}'],
        EmailTemplateType.reminder_invoice: ['{invoice_number}', '{due_date}'],
        EmailTemplateType.payment_failed: ['{invoice_number}', '{client_name}'],
    }

    for template_type, expected_placeholders in expected_vars.items():
        template = db.query(EmailTemplate).filter(
            EmailTemplate.template_type == template_type
        ).first()

        for placeholder in expected_placeholders:
            assert placeholder in template.subject or placeholder in template.body, \
                f"Template {template_type.value} missing {placeholder}"


def test_template_html_format(db):
    """Test that template bodies contain HTML."""
    templates = db.query(EmailTemplate).all()

    for template in templates:
        assert '<html>' in template.body.lower(), \
            f"Template {template.template_type.value} missing HTML tags"
        assert '</html>' in template.body.lower()


def test_get_all_active_templates(db):
    """Test retrieving all active templates."""
    active = db.query(EmailTemplate).filter(
        EmailTemplate.is_active == True
    ).all()

    assert len(active) == 9


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
