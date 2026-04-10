import { forwardRef } from 'react';

const Table = forwardRef(({ className = '', ...props }, ref) => (
  <div className="w-full overflow-x-auto">
    <table
      ref={ref}
      className={`w-full caption-bottom text-sm ${className}`}
      {...props}
    />
  </div>
));
Table.displayName = 'Table';

const TableHeader = forwardRef(({ className = '', ...props }, ref) => (
  <thead ref={ref} className={`border-b bg-gray-50 [&_tr]:border-b ${className}`} {...props} />
));
TableHeader.displayName = 'TableHeader';

const TableBody = forwardRef(({ className = '', ...props }, ref) => (
  <tbody ref={ref} className={`[&_tr:last-child]:border-0 ${className}`} {...props} />
));
TableBody.displayName = 'TableBody';

const TableRow = forwardRef(({ className = '', ...props }, ref) => (
  <tr
    ref={ref}
    className={`border-b transition-colors hover:bg-gray-50 data-[state=selected]:bg-gray-100 ${className}`}
    {...props}
  />
));
TableRow.displayName = 'TableRow';

const TableHead = forwardRef(({ className = '', ...props }, ref) => (
  <th
    ref={ref}
    className={`h-12 px-4 text-left align-middle font-medium text-gray-700 [&:has([role=checkbox])]:pr-0 ${className}`}
    {...props}
  />
));
TableHead.displayName = 'TableHead';

const TableCell = forwardRef(({ className = '', ...props }, ref) => (
  <td
    ref={ref}
    className={`px-4 py-3 align-middle [&:has([role=checkbox])]:pr-0 ${className}`}
    {...props}
  />
));
TableCell.displayName = 'TableCell';

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell };
