import React from 'react';
import { Eye } from 'lucide-react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="border-t border-slate-100 bg-white">
      <div className="max-w-7xl mx-auto px-4 py-12 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-2">
            <Eye className="text-emerald-600 w-6 h-6" />
            <span className="font-bold text-lg tracking-wide text-gray-900">Authentic<span className="text-emerald-600">Eye</span></span>
        </div>
        <div className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} AuthenticEye. All rights reserved.
        </div>
        <div className="flex gap-4 text-sm text-gray-400">
            <Link to="#" className="hover:text-accent">Privacy Policy</Link>
            <Link to="#" className="hover:text-accent">Terms of Service</Link>
            <Link to="#" className="hover:text-accent">API Docs</Link>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
