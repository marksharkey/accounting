import { forwardRef } from 'react';

const Input = forwardRef(({ className = '', ...props }, ref) => (
  <input
    ref={ref}
    className={`
      flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2
      text-base placeholder:text-gray-500 focus-visible:outline-none
      focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
      disabled:cursor-not-allowed disabled:opacity-50 appearance-none
      ${className}
    `}
    {...props}
  />
));
Input.displayName = 'Input';

export default Input;
