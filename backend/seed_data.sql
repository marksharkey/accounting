-- Seed Data for PrecisionPros Accounting System
-- This script populates sample data for testing and development

-- Chart of Accounts
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

-- Service Catalog
INSERT INTO service_catalog (name, description, default_amount, default_cycle, category, income_account_id, is_active, created_at, updated_at) VALUES
('Basic Web Hosting', 'Shared hosting with 10 GB storage', 29.99, 'monthly', 'Hosting', 1, TRUE, NOW(), NOW()),
('Premium Web Hosting', 'Dedicated hosting with 100 GB storage', 79.99, 'monthly', 'Hosting', 1, TRUE, NOW(), NOW()),
('Managed Services', 'Full server management and monitoring', 199.99, 'monthly', 'Managed Services', 2, TRUE, NOW(), NOW()),
('Security Monitoring', '24/7 security monitoring service', 49.99, 'monthly', 'Managed Services', 2, TRUE, NOW(), NOW()),
('Consulting - Hourly', 'IT consulting services (hourly)', 150.00, 'one_off', 'Consulting', 3, TRUE, NOW(), NOW()),
('Annual Maintenance', 'Annual system maintenance and updates', 599.99, 'annual', 'Hosting', 1, TRUE, NOW(), NOW());

-- Clients
INSERT INTO clients (company_name, contact_name, email, email_cc, phone, billing_type, account_status, account_balance, late_fee_type, late_fee_amount, late_fee_grace_days, notes, is_active, created_at, updated_at) VALUES
('Acme Corporation', 'John Smith', 'john@acmecorp.com', NULL, '555-0001', 'fixed_recurring', 'active', -1500.00, 'flat', 50.00, 15, 'Long-time client, always pays on time', TRUE, NOW(), NOW()),
('Global Tech Solutions', 'Sarah Johnson', 'billing@globaltech.com', 'sarah@globaltech.com', '555-0002', 'fixed_recurring', 'active', -2850.00, 'percentage', 5.00, 10, 'Large account, multiple services', TRUE, NOW(), NOW()),
('Small Business LLC', 'Mike Davis', 'admin@smallbiz.com', NULL, '555-0003', 'authnet_recurring', 'active', -400.00, 'none', 0.00, 0, 'New client, started in March 2026', TRUE, NOW(), NOW()),
('Enterprise Solutions Inc', 'Patricia Brown', 'pat@enterprise.com', 'finance@enterprise.com', '555-0004', 'mixed', 'active', -5200.00, 'flat', 75.00, 5, 'Premium client with multiple contracts', TRUE, NOW(), NOW());

-- Billing Schedules
-- Acme Corporation: Basic Hosting + Managed Services
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, authnet_recurring, is_active, notes, created_at, updated_at) VALUES
(1, 1, 'Basic Web Hosting', 29.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 10 DAY), FALSE, TRUE, 'Basic hosting plan', NOW(), NOW()),
(1, 3, 'Managed Services', 199.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 5 DAY), FALSE, TRUE, 'Full server management', NOW(), NOW());

-- Global Tech Solutions: Premium Hosting + Security Monitoring
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, authnet_recurring, is_active, notes, created_at, updated_at) VALUES
(2, 2, 'Premium Web Hosting', 79.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 15 DAY), FALSE, TRUE, 'Premium hosting with 100 GB', NOW(), NOW()),
(2, 4, 'Security Monitoring', 49.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 15 DAY), FALSE, TRUE, '24/7 monitoring', NOW(), NOW()),
(2, 6, 'Annual Maintenance', 599.99, 'annual', DATE_ADD(CURDATE(), INTERVAL 45 DAY), FALSE, TRUE, 'Annual contract', NOW(), NOW());

-- Small Business LLC: Basic Hosting via AuthNet
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, authnet_recurring, is_active, notes, created_at, updated_at) VALUES
(3, 1, 'Basic Web Hosting', 29.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 3 DAY), TRUE, TRUE, 'Basic hosting, auto-recurring', NOW(), NOW());

-- Enterprise Solutions Inc: Multiple Services
INSERT INTO billing_schedules (client_id, service_id, description, amount, cycle, next_bill_date, authnet_recurring, is_active, notes, created_at, updated_at) VALUES
(4, 2, 'Premium Web Hosting', 79.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, 'Premium hosting', NOW(), NOW()),
(4, 3, 'Managed Services', 199.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, 'Full management', NOW(), NOW()),
(4, 4, 'Security Monitoring', 49.99, 'monthly', DATE_ADD(CURDATE(), INTERVAL 20 DAY), FALSE, TRUE, '24/7 monitoring', NOW(), NOW()),
(4, 5, 'Consulting - Hourly', 1500.00, 'one_off', DATE_ADD(CURDATE(), INTERVAL 30 DAY), FALSE, TRUE, 'As-needed consulting', NOW(), NOW());

-- Create some sample invoices for testing
-- Note: invoice_number will need to follow the sequence, assuming we're at 0001 for 2026
INSERT INTO invoices (invoice_number, client_id, created_date, due_date, status, subtotal, total, amount_paid, balance_due, notes, created_at, updated_at) VALUES
('PP-2026-0001', 1, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'paid', 229.98, 229.98, 229.98, 0.00, 'Sample invoice 1', NOW(), NOW()),
('PP-2026-0002', 2, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'paid', 729.97, 729.97, 729.97, 0.00, 'Sample invoice 2', NOW(), NOW()),
('PP-2026-0003', 3, DATE_SUB(CURDATE(), INTERVAL 15 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'sent', 29.99, 29.99, 0.00, 29.99, 'Sample invoice 3 - Due Soon', NOW(), NOW()),
('PP-2026-0004', 4, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'sent', 1829.97, 1829.97, 0.00, 1829.97, 'Sample invoice 4 - Multi-service', NOW(), NOW()),
('PP-2026-0005', 1, DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 15 DAY), 'draft', 229.98, 229.98, 0.00, 229.98, 'Sample invoice 5 - Draft', NOW(), NOW());

-- Invoice Line Items
INSERT INTO invoice_line_items (invoice_id, service_id, description, quantity, unit_amount, amount, is_prorated, sort_order) VALUES
(1, 1, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(1, 3, 'Managed Services', 1, 199.99, 199.99, FALSE, 2),
(2, 2, 'Premium Web Hosting', 1, 79.99, 79.99, FALSE, 1),
(2, 4, 'Security Monitoring', 1, 49.99, 49.99, FALSE, 2),
(2, 6, 'Annual Maintenance', 1, 599.99, 599.99, FALSE, 3),
(3, 1, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(4, 2, 'Premium Web Hosting', 1, 79.99, 79.99, FALSE, 1),
(4, 3, 'Managed Services', 1, 199.99, 199.99, FALSE, 2),
(4, 4, 'Security Monitoring', 1, 49.99, 49.99, FALSE, 3),
(4, 5, 'Consulting - Hourly', 10, 150.00, 1500.00, FALSE, 4),
(5, 1, 'Basic Web Hosting', 1, 29.99, 29.99, FALSE, 1),
(5, 3, 'Managed Services', 1, 199.99, 199.99, FALSE, 2);

-- Sample Payments
INSERT INTO payments (invoice_id, client_id, payment_date, amount, method, reference_number, notes, reconciled, created_at) VALUES
(1, 1, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 229.98, 'credit_card', 'CC-12345', 'Online payment', TRUE, NOW()),
(2, 2, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 729.97, 'authnet', 'AUTH-67890', 'Recurring charge', TRUE, NOW());

-- Sample Expenses
INSERT INTO expenses (expense_date, vendor, description, amount, category_id, notes, reconciled, created_at, updated_at) VALUES
(DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'GoDaddy', 'Domain renewals for 5 domains', 85.00, 5, 'Annual domain fees', TRUE, NOW(), NOW()),
(DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'Microsoft', 'Office 365 subscription (5 seats)', 65.00, 5, 'Monthly software license', TRUE, NOW(), NOW()),
(DATE_SUB(CURDATE(), INTERVAL 3 DAY), 'Amazon', 'Server equipment and RAM upgrade', 450.00, 9, 'Equipment purchase', FALSE, NOW(), NOW());

-- Note: Update client account balances based on invoices
UPDATE clients SET account_balance = -2289.98 WHERE id = 1;
UPDATE clients SET account_balance = -2459.97 WHERE id = 2;
UPDATE clients SET account_balance = -329.99 WHERE id = 3;
UPDATE clients SET account_balance = -1829.97 WHERE id = 4;
