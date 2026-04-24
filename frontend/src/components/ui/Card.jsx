import { forwardRef } from 'react';

const Card = forwardRef(({ className = '', ...props }, ref) => (
  <div
    ref={ref}
    className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}
    {...props}
  />
));
Card.displayName = 'Card';

const CardHeader = forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`flex flex-col space-y-1.5 px-4 py-3 ${className}`} {...props} />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = forwardRef(({ className = '', ...props }, ref) => (
  <h2
    ref={ref}
    className={`text-sm font-semibold uppercase tracking-wide text-gray-500 ${className}`}
    {...props}
  />
));
CardTitle.displayName = 'CardTitle';

const CardDescription = forwardRef(({ className = '', ...props }, ref) => (
  <p ref={ref} className={`text-sm text-gray-600 ${className}`} {...props} />
));
CardDescription.displayName = 'CardDescription';

const CardContent = forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`px-4 pb-3 pt-0 ${className}`} {...props} />
));
CardContent.displayName = 'CardContent';

const CardFooter = forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`flex items-center p-6 pt-0 ${className}`} {...props} />
));
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
