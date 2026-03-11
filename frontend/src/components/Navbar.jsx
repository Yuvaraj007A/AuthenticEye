import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X, Eye } from 'lucide-react';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  return (
    <nav className="fixed w-full z-50 glass-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Eye className="text-emerald-600 w-8 h-8" />
            <span className="font-bold text-xl tracking-wide text-gray-900">Authentic<span className="text-emerald-600">Eye</span></span>
          </Link>

          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-6">
              <Link to="/" className="text-gray-700 hover:text-emerald-600 font-medium transition-colors">Home</Link>
              <Link to="/demo" className="text-gray-700 hover:text-emerald-600 font-medium transition-colors">Demo</Link>
              {token ? (
                <>
                  <Link to="/dashboard" className="text-gray-700 hover:text-emerald-600 font-medium transition-colors">Dashboard</Link>
                  <button onClick={handleLogout} className="text-red-500 hover:text-red-600 font-medium transition-colors">Logout</button>
                </>
              ) : (
                <>
                  <Link to="/login" className="text-gray-700 hover:text-emerald-600 font-medium transition-colors">Login</Link>
                  <Link to="/register" className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm">Sign Up</Link>
                </>
              )}
            </div>
          </div>

          <div className="-mr-2 flex md:hidden">
            <button onClick={() => setIsOpen(!isOpen)} className="text-slate-600 hover:text-slate-900">
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {isOpen && (
        <div className="md:hidden glass-card absolute w-full left-0 border-t border-white/10">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 text-center">
            <Link to="/" className="block px-3 py-2 text-base font-medium hover:text-accent">Home</Link>
            <Link to="/demo" className="block px-3 py-2 text-base font-medium hover:text-accent">Demo</Link>
            {token ? (
              <>
                <Link to="/dashboard" className="block px-3 py-2 text-base font-medium hover:text-accent">Dashboard</Link>
                <button onClick={handleLogout} className="block w-full px-3 py-2 text-base font-medium text-red-400">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="block px-3 py-2 text-base font-medium hover:text-accent">Login</Link>
                <Link to="/register" className="block px-3 py-2 text-base font-medium text-accent">Sign Up</Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
