import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, ShieldX, Image, Film, Mic, Trash2, 
  RefreshCw, FileText, ChevronLeft, ChevronRight, Search 
} from 'lucide-react';

const ICON_MAP = { image: Image, video: Film, audio: Mic };

const HistoryCard = ({ item, onDelete, onDownload }) => {
  const isFake = item.deepfakeProbability > 0.5;
  const MediaIcon = ICON_MAP[item.mediaType] || Image;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={`bg-white rounded-2xl border p-4 flex flex-col sm:flex-row sm:items-center gap-4 shadow-sm transition-all hover:shadow-md
        ${isFake ? 'border-rose-100' : 'border-emerald-100'}`}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className={`p-3 rounded-xl flex-shrink-0 ${isFake ? 'bg-rose-50' : 'bg-emerald-50'}`}>
          <MediaIcon size={20} className={isFake ? 'text-rose-500' : 'text-emerald-600'} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isFake
              ? <ShieldX size={14} className="text-rose-500 flex-shrink-0" />
              : <ShieldCheck size={14} className="text-emerald-500 flex-shrink-0" />
            }
            <span className={`text-sm font-black tracking-tight ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
              {isFake ? 'MANIPULATED / FAKE' : 'AUTHENTIC / REAL'}
            </span>
            <span className="text-[10px] text-slate-400 capitalize bg-slate-50 px-2 py-0.5 rounded-full font-bold">{item.mediaType}</span>
            {item.modelVersion && (
              <span className="text-[10px] text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full font-bold">{item.modelVersion}</span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Filename: <span className="font-mono text-slate-700">{item.fileUrl.split('/').pop()}</span>
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            Verdict: <strong>{isFake ? 'Fake' : 'Real'}</strong>
            {' '}·{' '}
            {new Date(item.createdAt).toLocaleDateString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 justify-end border-t border-slate-50 sm:border-t-0 pt-3 sm:pt-0">
        <button
          onClick={() => onDownload(item._id)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 transition"
        >
          <FileText size={14} /> PDF Report
        </button>
        <button
          onClick={() => onDelete(item._id)}
          className="p-2 rounded-xl text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </motion.div>
  );
};

const AnalysisHistory = ({ refreshTrigger }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Search, Filter, Pagination, Sort states
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState('newest');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.get('/history', {
        params: {
          page,
          limit: 6,
          search,
          filter,
          sort
        }
      });
      setHistory(res.data.data || []);
      setTotalPages(res.data.pages || 1);
      setTotalCount(res.data.total || 0);
    } catch (err) {
      setError('Could not load history. Are you logged in?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, filter, sort, refreshTrigger]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this analysis from history?')) return;
    try {
      await api.delete(`/history/${id}`);
      fetchHistory();
    } catch {
      alert('Delete failed');
    }
  };

  const handleDownloadPDF = async (id) => {
    try {
      const res = await api.get(`/history/${id}/report`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `AuthenticEye_Report_${id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF report.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900">Forensic Investigation Logs</h2>
          <p className="text-sm text-slate-500 font-medium">{totalCount} historical logs registered</p>
        </div>
        <button
          onClick={fetchHistory}
          className="flex items-center gap-2 px-4 py-2 self-start rounded-xl border border-slate-200 text-sm font-bold text-slate-600 hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Control Panel (Search, Filter, Sort) */}
      <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 flex flex-col md:flex-row gap-4 items-center">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:flex-1">
          <input
            type="text"
            placeholder="Search logs by filename..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <Search className="absolute left-3.5 top-3 text-slate-400" size={18} />
          <button type="submit" className="hidden">Search</button>
        </form>

        <div className="flex gap-3 w-full md:w-auto">
          <select
            value={filter}
            onChange={(e) => { setFilter(e.target.value); setPage(1); }}
            className="flex-1 md:w-40 px-3 py-2.5 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">Filter: All Results</option>
            <option value="real">Authentic Only</option>
            <option value="fake">Manipulated Only</option>
          </select>

          <select
            value={sort}
            onChange={(e) => { setSort(e.target.value); setPage(1); }}
            className="flex-1 md:w-44 px-3 py-2.5 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="newest">Sort: Newest First</option>
            <option value="oldest">Sort: Oldest First</option>
            <option value="confidence_high">Confidence: High to Low</option>
            <option value="confidence_low">Confidence: Low to High</option>
          </select>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-20 text-slate-400">
          <RefreshCw size={36} className="animate-spin mx-auto mb-3 text-indigo-500" />
          <p className="font-bold text-sm tracking-wider uppercase">Fetching logs...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-12 text-rose-500 font-bold">{error}</div>
      )}

      {/* Empty State */}
      {!loading && history.length === 0 && (
        <div className="text-center py-20 bg-white border border-slate-100 rounded-2xl shadow-sm">
          <ShieldCheck size={56} className="mx-auto mb-4 text-slate-200" />
          <p className="text-lg font-black text-slate-800">No logs found</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">No records match the current search or filters. Run a new detection to populate.</p>
        </div>
      )}

      {/* Logs List */}
      {!loading && history.length > 0 && (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {history.map(item => (
              <HistoryCard 
                key={item._id} 
                item={item} 
                onDelete={handleDelete} 
                onDownload={handleDownloadPDF} 
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500 font-medium">Page {page} of {totalPages}</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className={`p-2 rounded-lg border text-slate-600 transition ${page === 1 ? 'border-slate-100 text-slate-300 cursor-not-allowed' : 'border-slate-200 hover:bg-slate-50'}`}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className={`p-2 rounded-lg border text-slate-600 transition ${page === totalPages ? 'border-slate-100 text-slate-300 cursor-not-allowed' : 'border-slate-200 hover:bg-slate-50'}`}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisHistory;
