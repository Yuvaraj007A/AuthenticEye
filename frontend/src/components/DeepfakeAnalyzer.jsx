import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, AlertCircle, Loader2, Image as ImageIcon, Film } from 'lucide-react';
import api from '../services/api';
import ResultCard from './ResultCard';
import HeatmapViewer from './HeatmapViewer';

const TABS = [
  {
    key: 'image',
    label: 'Image',
    icon: ImageIcon,
    accept: 'image/*',
    route: '/detect/image',
    field: 'image',
    maxMB: 15,
    hint: 'JPEG · PNG · WEBP',
  },
  {
    key: 'video',
    label: 'Video',
    icon: Film,
    accept: 'video/*',
    route: '/detect/video',
    field: 'video',
    maxMB: 500,
    hint: 'MP4 · MOV · AVI · WEBM',
  },
];

const DeepfakeAnalyzer = ({ onResult }) => {
  const [activeTab, setActiveTab] = useState('image');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  const currentTab = TABS.find(t => t.key === activeTab);

  const reset = useCallback(() => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError('');
    setProgress(0);
  }, []);

  const handleTabChange = (key) => {
    setActiveTab(key);
    reset();
  };

  const handleFile = (selected) => {
    if (!selected) return;
    const maxBytes = currentTab.maxMB * 1024 * 1024;
    if (selected.size > maxBytes) {
      setError(`File exceeds ${currentTab.maxMB}MB limit`);
      return;
    }
    setFile(selected);
    setError('');
    if (selected.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(selected));
    } else {
      setPreview(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError('');
    setProgress(5);

    const formData = new FormData();
    formData.append(currentTab.field, file);

    const startTime = performance.now();

    try {
      const res = await api.post(currentTab.route, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          const up = Math.round((e.loaded / e.total) * 50);
          setProgress(up);
        },
      });
      const endTime = performance.now();
      const timeInSecs = ((endTime - startTime) / 1000).toFixed(2);
      
      setProgress(100);
      const outputData = { ...res.data, analysisTimeSeconds: timeInSecs };
      setResult(outputData);
      if (onResult) onResult(outputData);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.msg ||
        'Analysis failed. Please ensure the AI service is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">

      {/* ─── Tab Switcher ─────────────────────────── */}
      <div className="flex gap-1 p-1 bg-slate-100 rounded-2xl w-fit mx-auto shadow-inner">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
              activeTab === tab.key
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─── Upload Zone ──────────────────────────── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          <div
            className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all
              ${dragOver ? 'border-emerald-400 bg-emerald-50/60 scale-[1.01]' : ''}
              ${file ? 'border-emerald-300 bg-emerald-50/20' : !dragOver ? 'border-slate-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/10' : ''}
              ${!file ? 'cursor-pointer' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => !file && fileRef.current.click()}
          >
            {!file ? (
              <div className="flex flex-col items-center gap-4 py-10">
                <motion.div
                  animate={{ y: dragOver ? -8 : 0 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                  className="p-5 bg-emerald-50 rounded-2xl border border-emerald-100 shadow-sm"
                >
                  <currentTab.icon size={44} className="text-emerald-500" />
                </motion.div>
                <div>
                  <h3 className="font-bold text-xl text-gray-900 mb-1">
                    Drop your {currentTab.label.toLowerCase()} here
                  </h3>
                  <p className="text-slate-500 text-sm">or click to browse files</p>
                </div>
                <span className="px-4 py-2 bg-slate-100 rounded-full text-xs text-slate-500 font-medium">
                  {currentTab.hint} · Max {currentTab.maxMB}MB
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-5">
                {preview ? (
                  <img
                    src={preview}
                    alt="Preview"
                    className="max-h-60 rounded-xl shadow-md object-contain border border-slate-100"
                  />
                ) : (
                  <div className="flex items-center gap-3 p-4 bg-emerald-50 rounded-xl border border-emerald-100 w-full max-w-xs">
                    <currentTab.icon size={28} className="text-emerald-500" />
                    <div className="text-left min-w-0">
                      <p className="font-semibold text-gray-900 text-sm truncate">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); reset(); }}
                    className="px-5 py-2.5 rounded-xl border border-slate-200 text-slate-600 font-medium text-sm hover:bg-slate-50 transition"
                  >
                    Remove
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); analyze(); }}
                    disabled={loading}
                    className="px-7 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm flex items-center gap-2 transition disabled:opacity-60 shadow-sm"
                  >
                    {loading
                      ? <><Loader2 size={16} className="animate-spin" /> Analyzing...</>
                      : <><UploadCloud size={16} /> Run Forensic Analysis</>}
                  </button>
                </div>
              </div>
            )}
            <input
              type="file"
              ref={fileRef}
              className="hidden"
              accept={currentTab.accept}
              onChange={e => handleFile(e.target.files?.[0])}
            />
          </div>
        </motion.div>
      </AnimatePresence>

      {/* ─── Progress ─────────────────────────────── */}
      {loading && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Running {activeTab === 'image' ? '6-module' : 'temporal LSTM'} analysis...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <motion.div
              className="bg-gradient-to-r from-emerald-500 to-violet-500 h-2 rounded-full"
              initial={{ width: '5%' }}
              animate={{ width: `${Math.max(progress, 8)}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
          <p className="text-center text-xs text-slate-400">
            {activeTab === 'image'
              ? 'EfficientNet · XceptionNet · ViT · Frequency · GAN Fingerprint · Diffusion'
              : 'Extracting frames → Face detection → CNN features → LSTM temporal analysis'}
          </p>
        </div>
      )}

      {/* ─── Error ────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700"
          >
            <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-sm">Analysis Error</p>
              <p className="text-xs mt-0.5 text-rose-600">{error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Results ──────────────────────────────── */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-4"
          >
            <ResultCard result={result} imageUrl={preview} />
            {result.aiDetail?.heatmap_base64 && activeTab === 'image' && (
              <HeatmapViewer
                heatmapBase64={result.aiDetail.heatmap_base64}
                originalUrl={preview}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DeepfakeAnalyzer;
