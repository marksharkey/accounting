import Sidebar from './Sidebar';

export default function Layout({ children, title }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />

      {/* Main content area with responsive margins for sidebar */}
      <main className="lg:ml-56 md:ml-16 pt-20 md:pt-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {title && <h2 className="text-2xl font-bold mb-6">{title}</h2>}
          {children}
        </div>
      </main>
    </div>
  );
}
