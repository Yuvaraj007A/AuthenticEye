import React from 'react';
import DeepfakeAnalyzer from '../components/DeepfakeAnalyzer';
import { motion } from 'framer-motion';
import { ShieldCheck, Zap } from 'lucide-react';

const Demo = () => {
  return (
    <div className="min-h-screen py-20 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm font-semibold mb-6">
            <ShieldCheck size={16} /> Live Forensic Detection Engine
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
            Detect <span className="text-gradient">Deepfakes</span> Instantly
          </h1>
          <p className="text-slate-600 max-w-2xl mx-auto text-lg">
            Upload any image, video clip, or audio file. Our 3-model ensemble — EfficientNet-B4, XceptionNet,
            and Vision Transformer — performs a live forensic analysis in seconds.
          </p>
          <div className="flex items-center justify-center gap-6 mt-6 text-sm text-slate-500">
            <span className="flex items-center gap-1"><Zap size={14} className="text-emerald-500" /> &lt;2s image analysis</span>
            <span className="flex items-center gap-1"><Zap size={14} className="text-violet-500" /> Grad-CAM heatmaps</span>
            <span className="flex items-center gap-1"><Zap size={14} className="text-rose-500" /> Video frame analysis</span>
          </div>
        </motion.div>

        {/* Analyzer */}
        <DeepfakeAnalyzer />

        {/* Disclaimer */}
        <p className="text-center text-xs text-slate-400 mt-8">
          Files are processed in-memory and deleted immediately. Not stored unless you are signed in.
        </p>
      </div>
    </div>
  );
};

export default Demo;
