# PrecisionPros Frontend

React + Vite frontend for the PrecisionPros billing system.

## Setup

```bash
npm install
npm run dev
```

The dev server will start on `http://localhost:5173`.

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **React Router v6** - Client-side routing
- **TanStack Query** - Server state management
- **Axios** - HTTP client with JWT auth interceptors
- **Tailwind CSS** - Utility-first CSS
- **Shadcn/ui patterns** - Reusable UI components
- **Zustand** - Client state management (auth)

## Architecture

### Directory Structure

```
src/
├── api/               # API client and configuration
├── components/        # Reusable React components
│   └── ui/           # Shadcn-style UI component library
├── pages/            # Page components (routed by React Router)
├── store/            # Client state (Zustand stores)
├── App.jsx           # Main app with routing
├── main.jsx          # Entry point
└── index.css         # Tailwind CSS + global styles
```

### Key Components

- **LoginPage** - JWT authentication form
- **DashboardPage** - Overview of business metrics (MRR, ARR, overdue, daily queue)
- **ClientsListPage** - Searchable client table with pagination
- **ClientDetailPage** - Client profile with invoices, schedules, activity log
- **InvoiceBuilderPage** - Create/draft invoices with line items

### API Client

The API client (`src/api/client.js`) automatically:
- Adds JWT token from localStorage to all requests as `Authorization: Bearer <token>`
- Redirects to login on 401 Unauthorized responses
- Proxies all requests to `http://localhost:8010/api`

### Auth Store

Managed with Zustand (`src/store/authStore.js`):
- Stores JWT token in localStorage as `pp_token`
- Provides `login(username, password)` action
- Provides `logout()` action
- Provides `me()` action to fetch current user info
- Handles auth errors

## Development

### Adding a New Page

1. Create a file in `src/pages/YourPageName.jsx`
2. Import the Layout component and UI components
3. Add the route to `App.jsx`
4. Use React Query for data fetching

### Adding a New UI Component

1. Create a file in `src/components/ui/YourComponent.jsx`
2. Export a React component (preferably with forwardRef)
3. Use Tailwind classes for styling
4. Follow the pattern in existing components

### Testing

For manual testing:
- Backend API must be running on `http://localhost:8010`
- Default dev users: `mark/mark` and `candace/candace`
- Test on `http://localhost:5173`

## Build

```bash
npm run build
```

Output goes to `dist/`.

## Environment

- Backend API: `http://localhost:8010`
- Frontend: `http://localhost:5173` (dev) / `http://localhost:3000` (production)
- Auth token key: `pp_token` (localStorage)

## Next Steps

- [ ] Add invoice PDF generation
- [ ] Add email preview/sending UI
- [ ] Add bulk actions to invoice list
- [ ] Add expense management page
- [ ] Add reporting/analytics pages
- [ ] Add form validation
- [ ] Add error boundaries
- [ ] Add loading skeletons
