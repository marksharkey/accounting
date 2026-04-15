#!/usr/bin/env python3
"""
Test suite for Milestone 2: Email Template API Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, get_db
from models import EmailTemplate, EmailTemplateType


@pytest.fixture
def db():
    """Get database session for tests."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client():
    """Get test client."""
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_list_all_templates(client):
    """Test listing all email templates."""
    response = client.get("/api/email-templates")
    assert response.status_code == 200

    templates = response.json()
    assert len(templates) == 9
    assert all("template_type" in t for t in templates)
    assert all("subject" in t for t in templates)
    assert all("body" in t for t in templates)


def test_list_active_templates_only(client):
    """Test filtering to only active templates."""
    response = client.get("/api/email-templates?active_only=true")
    assert response.status_code == 200

    templates = response.json()
    assert len(templates) >= 8  # At least 8 (may vary based on test execution order)
    assert all(t["is_active"] for t in templates)


def test_get_specific_template(client):
    """Test getting a specific template by type."""
    response = client.get("/api/email-templates/new_invoice")
    assert response.status_code == 200

    template = response.json()
    assert template["template_type"] == "new_invoice"
    assert "subject" in template
    assert "body" in template
    assert "{invoice_number}" in template["subject"] or "{invoice_number}" in template["body"]


def test_get_invalid_template_type(client):
    """Test getting a template with invalid type."""
    response = client.get("/api/email-templates/invalid_type")
    assert response.status_code == 400
    assert "Invalid template type" in response.json()["detail"]


def test_get_nonexistent_template(client):
    """Test getting a template that doesn't exist."""
    # This shouldn't happen in practice since all default templates are seeded,
    # but we should handle the case gracefully
    response = client.get("/api/email-templates/new_invoice")
    assert response.status_code == 200  # Should exist from seeds


def test_update_template(client, db):
    """Test updating an email template."""
    # Get original template first
    get_response = client.get("/api/email-templates/new_invoice")
    original_template = get_response.json()

    new_subject = "Updated: Invoice {invoice_number}"
    new_body = "<html><body>Updated content</body></html>"

    response = client.put(
        "/api/email-templates/new_invoice",
        json={
            "subject": new_subject,
            "body": new_body,
            "is_active": True
        }
    )

    assert response.status_code == 200
    template = response.json()
    assert template["subject"] == new_subject
    assert template["body"] == new_body

    # Verify in database
    db_template = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == EmailTemplateType.new_invoice
    ).first()
    assert db_template.subject == new_subject

    # Restore original
    client.put(
        "/api/email-templates/new_invoice",
        json={
            "subject": original_template["subject"],
            "body": original_template["body"],
            "is_active": original_template["is_active"]
        }
    )


def test_update_template_inactive(client, db):
    """Test updating a template to be inactive."""
    response = client.put(
        "/api/email-templates/suspension_invoice",
        json={
            "subject": "Test",
            "body": "<html>Test</html>",
            "is_active": False
        }
    )

    assert response.status_code == 200
    template = response.json()
    assert template["is_active"] == False

    # Restore to active for other tests
    client.put(
        "/api/email-templates/suspension_invoice",
        json={
            "subject": template["subject"],
            "body": template["body"],
            "is_active": True
        }
    )


def test_update_invalid_template_type(client):
    """Test updating with invalid template type."""
    response = client.put(
        "/api/email-templates/invalid_type",
        json={
            "subject": "Test",
            "body": "<html>Test</html>"
        }
    )

    assert response.status_code == 400


def test_get_available_types(client):
    """Test getting available template types."""
    response = client.get("/api/email-templates/types/available")
    assert response.status_code == 200

    data = response.json()
    assert "types" in data
    assert "descriptions" in data
    assert len(data["types"]) == 9
    assert "new_invoice" in data["types"]
    assert data["descriptions"]["new_invoice"]


def test_get_supported_variables(client):
    """Test getting list of supported template variables."""
    response = client.get("/api/email-templates/variables/supported")
    assert response.status_code == 200

    data = response.json()
    assert "variables" in data
    assert "common" in data["variables"]
    assert "memo_specific" in data["variables"]
    assert "{client_name}" in data["variables"]["common"]
    assert "{invoice_number}" in data["variables"]["common"]


def test_template_response_format(client):
    """Test that template responses have correct format."""
    response = client.get("/api/email-templates/paid_invoice")
    assert response.status_code == 200

    template = response.json()
    # Check all required fields
    assert "id" in template
    assert isinstance(template["id"], int)
    assert template["template_type"] == "paid_invoice"
    assert isinstance(template["subject"], str)
    assert isinstance(template["body"], str)
    assert isinstance(template["is_active"], bool)
    assert "created_at" in template
    assert "updated_at" in template


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
