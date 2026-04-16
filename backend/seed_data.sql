-- Seed Data for PrecisionPros Accounting System
-- This script populates sample data for testing and development

-- =====================================================
-- 1. Chart of Accounts
-- =====================================================
INSERT INTO chart_of_accounts (code, name, account_type, description, is_active, created_at) VALUES
('4100', 'Web Hosting Revenue', 'income', 'Monthly web hosting service revenue', TRUE, NOW()),
('4200', 'Managed Services Revenue', 'income', 'Managed IT services revenue', TRUE, NOW()),
('4300', 'Consulting Revenue', 'income', 'Consulting and hourly services', TRUE, NOW()),
('5100', 'Hosting Costs', 'expense', 'Cost of hosting services', TRUE, NOW()),
('5200', 'Software Licenses', 'expense', 'Software subscription costs', TRUE, NOW()),
('6100', 'Payroll', 'expense', 'Employee payroll (for Phase 2)', TRUE, NOW()),
('6200', 'Office Rent', 'expense', 'Office space rent', TRUE, NOW()),
('6300', 'Marketing', 'expense', 'Marketing and advertising', TRUE, NOW()),
('6400', 'Equipment', 'expense', 'Computer and office equipment', TRUE, NOW());

-- =====================================================
-- 2. Service Catalog
-- =====================================================
SET @coa_hosting_id = (SELECT id FROM chart_of_accounts WHERE code='4100' LIMIT 1);
SET @coa_managed_id = (SELECT id FROM chart_of_accounts WHERE code='4200' LIMIT 1);
SET @coa_consulting_id = (SELECT id FROM chart_of_accounts WHERE code='4300' LIMIT 1);

INSERT INTO service_catalog (name, description, default_amount, default_cycle, category, income_account_id, is_active, created_at, updated_at) VALUES
('Basic Web Hosting', 'Shared hosting with 10 GB storage', 29.99, 'monthly', 'Hosting', @coa_hosting_id, TRUE, NOW(), NOW()),
('Premium Web Hosting', 'Dedicated hosting with 100 GB storage', 79.99, 'monthly', 'Hosting', @coa_hosting_id, TRUE, NOW(), NOW()),
('Managed Services', 'Full server management and monitoring', 199.99, 'monthly', 'Managed Services', @coa_managed_id, TRUE, NOW(), NOW()),
('Security Monitoring', '24/7 security monitoring service', 49.99, 'monthly', 'Managed Services', @coa_managed_id, TRUE, NOW(), NOW()),
('Consulting - Hourly', 'IT consulting services (hourly)', 150.00, 'monthly', 'Consulting', @coa_consulting_id, TRUE, NOW(), NOW()),
('Annual Maintenance', 'Annual system maintenance and updates', 599.99, 'annual', 'Hosting', @coa_hosting_id, TRUE, NOW(), NOW());

-- =====================================================
-- 3. Clients
-- =====================================================
INSERT INTO clients (company_name, contact_name, email, email_cc, phone, autocc_recurring, account_status, account_balance, late_fee_type, late_fee_amount, late_fee_grace_days, notes, is_active, created_at, updated_at) VALUES
('Acme Corporation', 'John Smith', 'john@acmecorp.com', NULL, '555-0001', FALSE, 'active', -1500.00, 'flat', 50.00, 15, 'Long-time client, always pays on time', TRUE, NOW(), NOW()),
('Global Tech Solutions', 'Sarah Johnson', 'billing@globaltech.com', 'sarah@globaltech.com', '555-0002', FALSE, 'active', -2850.00, 'percentage', 5.00, 10, 'Large account, multiple services', TRUE, NOW(), NOW()),
('Small Business LLC', 'Mike Davis', 'admin@smallbiz.com', NULL, '555-0003', TRUE, 'active', -400.00, 'none', 0.00, 0, 'New client, started in March 2026', TRUE, NOW(), NOW()),
('Enterprise Solutions Inc', 'Patricia Brown', 'pat@enterprise.com', 'finance@enterprise.com', '555-0004', FALSE, 'active', -5200.00, 'flat', 75.00, 5, 'Premium client with multiple contracts', TRUE, NOW(), NOW());

-- =====================================================
-- 4. Billing Schedules
-- =====================================================
SET @client_acme = (SELECT id FROM clients WHERE company_name='Acme Corporation' LIMIT 1);
SET @client_global = (SELECT id FROM clients WHERE company_name='Global Tech Solutions' LIMIT 1);
SET @client_small = (SELECT id FROM clients WHERE company_name='Small Business LLC' LIMIT 1);
SET @client_enterprise = (SELECT id FROM clients WHERE company_name='Enterprise Solutions Inc' LIMIT 1);

SET @svc_basic_hosting = (SELECT id FROM service_catalog WHERE name='Basic Web Hosting' LIMIT 1);
SET @svc_premium_hosting = (SELECT id FROM service_catalog WHERE name='Premium Web Hosting' LIMIT 1);
SET @svc_managed = (SELECT id FROM service_catalog WHERE name='Managed Services' LIMIT 1);
SET @svc_security = (SELECT id FROM service_catalog WHERE name='Security Monitoring' LIMIT 1);
SET @svc_consulting = (SELECT id FROM service_catalog WHERE name='Consulting - Hourly' LIMIT 1);
SET @svc_maintenance = (SELECT id FROM service_catalog WHERE name='Annual Maintenance' LIMIT 1);

-- Acme Corporation: Basic Hosting + Managed Services
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, autocc_recurring, is_active, notes, created_at, updated_at) VALUES
(@client_acme, @svc_basic_hosting, 'Basic Web Hosting', 29.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 10 DAY), FALSE, TRUE, 'Basic hosting plan', NOW(), NOW()),
(@client_acme, @svc_managed, 'Managed Services', 199.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 5 DAY), FALSE, TRUE, 'Full server management', NOW(), NOW());

-- Global Tech Solutions: Premium Hosting + Security Monitoring + Maintenance
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, autocc_recurring, is_active, notes, created_at, updated_at) VALUES
(@client_global, @svc_premium_hosting, 'Premium Web Hosting', 79.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 15 DAY), FALSE, TRUE, 'Premium hosting with 100 GB', NOW(), NOW()),
(@client_global, @svc_security, 'Security Monitoring', 49.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 15 DAY), FALSE, TRUE, '24/7 monitoring', NOW(), NOW()),
(@client_global, @svc_maintenance, 'Annual Maintenance', 599.99, 'annual', DATE_ADD(CURDATE(), INTERVAL 45 DAY), FALSE, TRUE, 'Annual contract', NOW(), NOW());

-- Small Business LLC: Basic Hosting via AutoCC
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, autocc_recurring, is_active, notes, created_at, updated_at) VALUES
(@client_small, @svc_basic_hosting, 'Basic Web Hosting', 29.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 3 DAY), TRUE, TRUE, 'Basic hosting, auto-recurring', NOW(), NOW());

-- Enterprise Solutions Inc: Multiple Services
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, autocc_recurring, is_active, notes, created_at, updated_at) VALUES
(@client_enterprise, @svc_premium_hosting, 'Premium Web Hosting', 79.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, 'Premium hosting', NOW(), NOW()),
(@client_enterprise, @svc_managed, 'Managed Services', 199.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, 'Full management', NOW(), NOW()),
(@client_enterprise, @svc_security, 'Security Monitoring', 49.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, '24/7 monitoring', NOW(), NOW()),
(@client_enterprise, @svc_consulting, 'Consulting - Hourly', 1500.00, 'monthly', DATE_ADD(CURDATE(), INTERVAL 30 DAY), FALSE, TRUE, 'As-needed consulting', NOW(), NOW());

-- =====================================================
-- 5. Invoices
-- =====================================================
INSERT INTO invoices (invoice_number, client_id, created_date, due_date, status, subtotal, total, amount_paid, balance_due, notes, created_at, updated_at) VALUES
('PP-2026-0001', @client_acme, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'paid', 229.98, 229.98, 229.98, 0.00, 'Sample invoice 1 - Paid', NOW(), NOW()),
('PP-2026-0002', @client_global, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'paid', 729.97, 729.97, 729.97, 0.00, 'Sample invoice 2 - Paid', NOW(), NOW()),
('PP-2026-0003', @client_small, DATE_SUB(CURDATE(), INTERVAL 15 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'sent', 29.99, 29.99, 0.00, 29.99, 'Sample invoice 3 - Due Soon', NOW(), NOW()),
('PP-2026-0004', @client_enterprise, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'sent', 1829.97, 1829.97, 0.00, 1829.97, 'Sample invoice 4 - Multi-service', NOW(), NOW()),
('PP-2026-0005', @client_acme, DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 15 DAY), 'draft', 229.98, 229.98, 0.00, 229.98, 'Sample invoice 5 - Draft', NOW(), NOW());

-- =====================================================
-- 6. Invoice Line Items
-- =====================================================
SET @inv1 = (SELECT id FROM invoices WHERE invoice_number='PP-2026-0001' LIMIT 1);
SET @inv2 = (SELECT id FROM invoices WHERE invoice_number='PP-2026-0002' LIMIT 1);
SET @inv3 = (SELECT id FROM invoices WHERE invoice_number='PP-2026-0003' LIMIT 1);
SET @inv4 = (SELECT id FROM invoices WHERE invoice_number='PP-2026-0004' LIMIT 1);
SET @inv5 = (SELECT id FROM invoices WHERE invoice_number='PP-2026-0005' LIMIT 1);

INSERT INTO invoice_line_items (invoice_id, service_id, description, quantity, unit_amount, amount, is_prorated, sort_order) VALUES
(@inv1, @svc_basic_hosting, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(@inv1, @svc_managed, 'Managed Services', 1, 199.99, 199.99, FALSE, 2),
(@inv2, @svc_premium_hosting, 'Premium Web Hosting', 1, 79.99, 79.99, FALSE, 1),
(@inv2, @svc_security, 'Security Monitoring', 1, 49.99, 49.99, FALSE, 2),
(@inv2, @svc_maintenance, 'Annual Maintenance', 1, 599.99, 599.99, FALSE, 3),
(@inv3, @svc_basic_hosting, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(@inv4, @svc_premium_hosting, 'Premium Web Hosting', 1, 79.99, 79.99, FALSE, 1),
(@inv4, @svc_managed, 'Managed Services', 1, 199.99, 199.99, FALSE, 2),
(@inv4, @svc_security, 'Security Monitoring', 1, 49.99, 49.99, FALSE, 3),
(@inv4, @svc_consulting, 'Consulting - Hourly', 10, 150.00, 1500.00, FALSE, 4),
(@inv5, @svc_basic_hosting, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(@inv5, @svc_managed, 'Managed Services', 1, 199.99, 199.99, FALSE, 2);

-- =====================================================
-- 7. Payments
-- =====================================================
INSERT INTO payments (invoice_id, client_id, payment_date, amount, method, reference_number, notes, reconciled, created_at) VALUES
(@inv1, @client_acme, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 229.98, 'credit_card', 'CC-12345', 'Online payment', TRUE, NOW()),
(@inv2, @client_global, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 729.97, 'autocc', 'AUTOCC-67890', 'Recurring charge', TRUE, NOW());

-- =====================================================
-- 8. Invoice Sequence
-- =====================================================
INSERT INTO invoice_sequences (prefix, last_number, year) VALUES ('PP', 5, 2026);

-- =====================================================
-- 9. Expenses
-- =====================================================
SET @coa_software = (SELECT id FROM chart_of_accounts WHERE code='5200' LIMIT 1);
SET @coa_equipment = (SELECT id FROM chart_of_accounts WHERE code='6400' LIMIT 1);

INSERT INTO expenses (expense_date, vendor, description, amount, category_id, notes, reconciled, created_at, updated_at) VALUES
(DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'GoDaddy', 'Domain renewals for 5 domains', 85.00, @coa_software, 'Annual domain fees', TRUE, NOW(), NOW()),
(DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'Microsoft', 'Office 365 subscription (5 seats)', 65.00, @coa_software, 'Monthly software license', TRUE, NOW(), NOW()),
(DATE_SUB(CURDATE(), INTERVAL 3 DAY), 'Amazon', 'Server equipment and RAM upgrade', 450.00, @coa_equipment, 'Equipment purchase', FALSE, NOW(), NOW());
