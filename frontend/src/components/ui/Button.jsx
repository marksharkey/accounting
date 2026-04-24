import { forwardRef } from 'react';

const variants = {
  default: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
  outline: 'border border-gray-300 text-gray-900 hover:bg-gray-50',
  ghost: 'text-gray-700 hover:bg-gray-100',
};

const sizes = {
  default: 'px-3 py-1 text-xs',
  sm: 'px-2 py-0.5 text-xs',
  lg: 'px-4 py-1.5 text-sm',
};

const Button = forwardRef(
  ({ className = '', variant = 'default', size = 'default', disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`
          inline-flex items-center justify-center rounded font-medium
          transition-colors focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
          ${variants[variant]} ${sizes[size]} ${className}
        `}
        disabled={disabled}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
export default Button;
