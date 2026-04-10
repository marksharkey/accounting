export function formatBillingType(billingType) {
  const formatMap = {
    fixed_recurring: 'Fixed Recurring',
    authnet_recurring: 'Auth.net Recurring',
    mixed: 'Mixed',
    one_off: 'One Off',
  };

  return formatMap[billingType] || billingType || 'Unknown';
}
