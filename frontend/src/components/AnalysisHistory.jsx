import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldX, Image, Film, Mic, Trash2, RefreshCw } from 'lucide-react';

const ICON_MAP = { image: Image, video: Film, audio: Mic };

const HistoryCard = ({ item, onDelete }) => {
  const isFake = item.deepfakeProbability > 0.5;
  const MediaIcon = ICON_MAP[item.mediaType] || Image;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={`bg-white rounded-2xl border p-4 flex items-center gap-4 shadow-sm transition-all hover:shadow-md
        ${isFake ? 'border-rose-100' : 'border-emerald-100'}`}
    >
      <div className={`p-3 rounded-xl ${isFake ? 'bg-rose-50' : 'bg-emerald-50'}`}>
        <MediaIcon size={20} className={isFake ? 'text-rose-500' : 'text-emerald-600'} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {isFake
            ? <ShieldX size={14} className="text-rose-500 flex-shrink-0" />
            : <ShieldCheck size={14} className="text-emerald-500 flex-shrink-0" />
          }
          <span className={`text-sm font-bold ${isFake ? 'text-rose-700' : 'text-emerald-700'}`}>
            {isFake ? 'MANIPULATED' : 'AUTHENTIC'}
          </span>
          <span className="text-xs text-slate-400 capitalize bg-slate-50 px-2 py-0.5 rounded-full">{item.mediaType}</span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">
          Deepfake: <strong>{(item.deepfakeProbability * 100).toFixed(1)}%</strong>
          {' '}·{' '}
          {new Date(item.createdAt).toLocaleDateString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}
        </p>
      </div>

      <button
        onClick={() => onDelete(item._id)}
        className="p-2 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition"
      >
        <Trash2 size={16} />
      </button>
    </motion.div>
  );
};

const AnalysisHistory = ({ refreshTrigger }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.get('/history');
      setHistory(res.data);
    } catch (err) {
      setError('Could not load history. Are you logged in?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, [refreshTrigger]);

  const handleDelete = async (id) => {
    try {
      await api.delete(`/history/${id}`);
      setHistory(prev => prev.filter(h => h._id !== id));
    } catch {
      alert('Delete failed');
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Analysis History</h2>
          <p className="text-sm text-slate-500">{history.length} total records</p>
        </div>
        <button
          onClick={fetchHistory}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {loading && (
        <div className="text-center py-16 text-slate-400">
          <RefreshCw size={28} className="animate-spin mx-auto mb-3" />
          Loading history...
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-rose-500">{error}</div>
      )}

      {!loading && history.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <ShieldCheck size={40} className="mx-auto mb-3 text-slate-200" />
          <p className="font-medium">No analyses yet.</p>
          <p className="text-sm">Run a detection and results will appear here.</p>
        </div>
      )}

      <div className="space-y-3">
        {history.map(item => (
          <HistoryCard key={item._id} item={item} onDelete={handleDelete} />
        ))}
      </div>
    </div>
  );
};

export default AnalysisHistory;
