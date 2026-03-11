import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DeepfakeAnalyzer from '../components/DeepfakeAnalyzer';
import AnalysisHistory from '../components/AnalysisHistory';
import { motion } from 'framer-motion';
import { ShieldCheck, History, LogOut } from 'lucide-react';

const DashboardLayout = () => {
  const navigate = useNavigate();
  const [activeView, setActiveView] = useState('scan');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) navigate('/login');
    else setIsAuthenticated(true);
  }, [navigate]);

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-slate-50/50">
      {/* Dashboard Header */}
      <div className="bg-white border-b border-slate-100 sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-50 rounded-xl border border-emerald-100">
              <ShieldCheck size={22} className="text-emerald-600" />
            </div>
            <div>
              <h1 className="font-bold text-gray-900">Client Portal</h1>
              <p className="text-xs text-slate-500">Forensic Detection Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex gap-1 p-1 bg-slate-100 rounded-xl">
              <button
                onClick={() => setActiveView('scan')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeView === 'scan' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
              >
                🔍 New Scan
              </button>
              <button
                onClick={() => setActiveView('history')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all flex items-center gap-1.5 ${activeView === 'history' ? 'bg-white text-violet-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
              >
                <History size={14} /> History
              </button>
            </div>
            <button
              onClick={() => { localStorage.removeItem('token'); navigate('/'); }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-rose-500 hover:bg-rose-50 transition font-medium"
            >
              <LogOut size={15} /> Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-10">
        {activeView === 'scan' ? (
          <motion.div
            key="scan"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <DeepfakeAnalyzer onResult={() => setRefreshTrigger(p => p + 1)} />
          </motion.div>
        ) : (
          <motion.div
            key="history"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <AnalysisHistory refreshTrigger={refreshTrigger} />
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default DashboardLayout;
