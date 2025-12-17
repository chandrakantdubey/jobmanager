import React, { useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Search, Globe, LogOut, Briefcase } from 'lucide-react';
import { clsx } from 'clsx';
import { Toaster } from 'react-hot-toast';
import Dashboard from './pages/Dashboard';
import SearchPage from './pages/Search';
import Login from './pages/Login';
import Register from './pages/Register';
import ScrapedJobs from './pages/ScrapedJobs';
import { AuthProvider, AuthContext } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

function NavItem({ to, icon: Icon, label }) {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link
      to={to}
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
        isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
      )}
    >
      <Icon size={20} />
      <span className="font-medium">{label}</span>
    </Link>
  );
}

function Sidebar() {
  const { logout, user } = useContext(AuthContext);

  return (
    <div className="w-64 bg-white border-r h-screen fixed left-0 top-0 p-4 flex flex-col">
      <div className="flex items-center gap-2 mb-8 px-4">
        <Briefcase className="text-blue-600" size={32} />
        <h1 className="text-xl font-bold">JobManager</h1>
      </div>

      <nav className="space-y-1 flex-1">
        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" />
        <NavItem to="/search" icon={Search} label="Find Jobs" />
        <NavItem to="/scraped" icon={Globe} label="Scraped Jobs" />
      </nav>

      <div className="border-t pt-4">
        <div className="px-4 mb-2">
          <p className="text-sm font-semibold truncate">{user?.username}</p>
          <p className="text-xs text-gray-500 truncate">{user?.email}</p>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 px-4 py-3 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
        >
          <LogOut size={20} />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <main className="ml-64 p-8">
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/" element={
            <ProtectedRoute>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          } />

          <Route path="/search" element={
            <ProtectedRoute>
              <Layout>
                <SearchPage />
              </Layout>
            </ProtectedRoute>
          } />

          <Route path="/scraped" element={
            <ProtectedRoute>
              <Layout>
                <ScrapedJobs />
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </Router>
      <Toaster position="top-right" />
    </AuthProvider >
  );
}

export default App;
