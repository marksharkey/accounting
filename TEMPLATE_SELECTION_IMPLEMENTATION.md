# Email Template Selection & Preview Implementation

## Summary
Implemented a modal-based workflow for selecting email templates and previewing them before sending invoices. Users now see a "Send" modal that defaults to the `new_invoice` template and allows switching between other active templates with a live preview.

## Changes Made

### Backend Changes

#### 1. `backend/services/email.py`
- **Added `_build_invoice_context(invoice, client)`**: Helper function to build the template context variables for invoice emails (extracted for reuse)
- **Updated `send_new_invoice_email()`**: Now delegates to `send_invoice_email_with_type()` 
- **Added `send_invoice_email_with_type(invoice, client, template_type)`**: New function that sends an invoice email with a specified template type, with PDF attachment fallback

#### 2. `backend/routers/invoices.py`
- **Imported new helpers**: `send_invoice_email_with_type`, `_get_template`, `_render_template_string`, `_build_invoice_context`
- **Added `/invoices/{invoice_id}/email-preview` (GET)**: 
  - Query parameter: `template_type` (default: "new_invoice")
  - Returns: `{ subject, body, template_type }`
  - Renders the selected template with invoice context variables
  - Used by frontend to show live preview

- **Updated `/invoices/{invoice_id}/send` (POST)**:
  - New query parameter: `template_type` (default: "new_invoice")
  - Converts string to EmailTemplateType enum
  - Sends with selected template
  - Returns: `{ invoice_id, status }`

- **Updated `/invoices/{invoice_id}/resend` (POST)**:
  - Same changes as `/send`
  - Allows users to resend with a different template

### Frontend Changes

#### 1. New Component: `frontend/src/components/SendInvoiceModal.jsx`
A new reusable modal component for sending/resending invoices with template selection:

**Props:**
- `isOpen` (boolean): Controls modal visibility
- `onClose` (function): Callback when modal closes
- `invoiceId` (number): ID of invoice to send
- `mode` (string): Either "send" or "resend"
- `onSuccess` (function): Callback after successful send

**Features:**
- Lists all active templates (excluding "default" fallback)
- Defaults to "new_invoice" template
- Shows human-readable labels for each template type:
  - `new_invoice` → "New Invoice (Default)"
  - `reminder_invoice` → "Payment Reminder"
  - `invoice_past_due` → "Past Due Notice"
  - `suspension_invoice` → "Suspension Warning"
  - `cancellation_invoice` → "Cancellation Notice"
- Live preview of:
  - Email subject (plain text)
  - Email body (rendered in iframe for safe HTML display)
- Fetches preview when modal opens or template selection changes
- Handles loading and error states
- Sends with selected template on confirmation

#### 2. Updated: `frontend/src/pages/InvoiceDetailPage.jsx`
- **Removed old mutations**: `sendMutation` and `resendMutation` (now handled by modal)
- **Added state**: `isSendModalOpen`, `sendModalMode`
- **Updated "Send" button** (draft invoices): Opens modal with mode="send"
- **Updated "Resend" button** (sent invoices): Opens modal with mode="resend"
- **Added `<SendInvoiceModal />` component** with proper prop passing
- **Retained "Mark as Sent" button** for marking sent without email

## How It Works

### User Flow: Sending an Invoice

1. User opens an invoice in draft status
2. Clicks "Send" button
3. Modal opens showing:
   - Dropdown with active template options (defaults to "New Invoice (Default)")
   - Preview of the selected template's subject and body
4. User can:
   - Switch to a different template (preview updates automatically)
   - Review the email that will be sent
5. Clicks "Send" to confirm
6. Invoice status changes to "sent" and email is dispatched with selected template
7. Modal closes and invoice detail page refreshes

### API Flow

**Preview Endpoint:**
```
GET /api/invoices/{invoice_id}/email-preview?template_type=new_invoice
```
Response:
```json
{
  "subject": "Invoice INV-001 from ACME Corp",
  "body": "<html>...</html>",
  "template_type": "new_invoice"
}
```

**Send Endpoint:**
```
POST /api/invoices/{invoice_id}/send?template_type=new_invoice
```
Response:
```json
{
  "invoice_id": 123,
  "status": "sent"
}
```

## Testing Checklist

1. **Setup Templates** (if not already done):
   - Go to Company Settings → Email Templates
   - Ensure "new_invoice" template is active and properly configured
   - Optionally configure other template types (reminder, past due, etc.)

2. **Test Draft Invoice Send**:
   - Create a new invoice (or open existing draft)
   - Click "Send" button
   - Verify modal opens with "New Invoice (Default)" pre-selected
   - Verify preview shows rendered email with invoice details
   - Switch to another template (e.g., "Payment Reminder")
   - Verify preview updates with new template content
   - Switch back to default
   - Click "Send" button
   - Verify invoice status changes to "sent"
   - Verify modal closes

3. **Test Resend**:
   - Open a sent invoice
   - Click "Resend" button
   - Verify same workflow as send
   - Verify template selection works

4. **Test Email Delivery**:
   - Check backend logs for email sending
   - Verify email was sent with correct template
   - Check email body contains rendered variables (invoice number, due date, amount, etc.)

5. **Test Edge Cases**:
   - Try opening modal with inactive templates (should not appear in list)
   - Verify default template is shown if selected template is inactive
   - Test with different invoice amounts and client names
   - Verify special characters in invoice data are properly escaped in HTML preview

## Technical Notes

- **EmailTemplateType Enum**: All template type strings are converted from URL query parameters to the enum type for database lookups
- **Template Fallback**: If a selected template is inactive, `_get_template()` falls back to the "default" template
- **HTML Safety**: Email body preview uses iframe with `srcDoc` prop for safe HTML rendering (prevents XSS)
- **Context Variables**: Template variables are rendered using Python's `str.format()` with invoice context
- **PDF Attachments**: Invoices are automatically attached to emails (with fallback if PDF generation fails)
- **Backward Compatibility**: The `/send` and `/resend` endpoints still work with the default template if no `template_type` is specified
