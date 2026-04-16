import Sidebar from './Sidebar';

export default function Layout({ children, title, onBack }) {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Sidebar />

      {/* Main content area — offset for sidebar, minimal side padding */}
      <main className="flex-1 min-w-0 pt-20 md:pt-0 md:ml-64">
        <div className="px-4 py-6">
          {(title || onBack) && (
            <div className="relative flex items-center justify-center mb-6">
              {onBack && (
                <button
                  onClick={onBack}
                  className="absolute left-0 text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center gap-1"
                >
                  ← Back
                </button>
              )}
              {title && <h2 className="text-2xl font-bold">{title}</h2>}
            </div>
          )}
          {children}
        </div>
      </main>
    </div>
  );
}
