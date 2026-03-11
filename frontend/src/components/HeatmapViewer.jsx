import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff } from 'lucide-react';

const HeatmapViewer = ({ heatmapBase64, originalUrl }) => {
  const [showHeatmap, setShowHeatmap] = useState(true);

  if (!heatmapBase64) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 bg-white rounded-2xl border border-slate-100 shadow-sm p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-bold text-gray-900 text-lg">Grad-CAM Explainability</h3>
          <p className="text-sm text-slate-500">Highlighted regions the model flagged as suspicious</p>
        </div>
        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition font-medium"
        >
          {showHeatmap ? <><EyeOff size={15} /> Hide</> : <><Eye size={15} /> Show</>}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {originalUrl && (
          <div>
            <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">Original</p>
            <img src={originalUrl} alt="Original" className="w-full rounded-xl object-contain max-h-64 bg-slate-50 border border-slate-100" />
          </div>
        )}
        {showHeatmap && (
          <div>
            <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">
              Heatmap Overlay
              <span className="ml-2 px-2 py-0.5 bg-rose-50 text-rose-600 rounded-full text-xs normal-case font-normal">
                🔴 Red = Suspicious Region
              </span>
            </p>
            <img
              src={`data:image/jpeg;base64,${heatmapBase64}`}
              alt="Heatmap"
              className="w-full rounded-xl object-contain max-h-64 bg-slate-50 border border-slate-100"
            />
          </div>
        )}
      </div>

      <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded-xl">
        <p className="text-xs text-amber-700">
          <strong>How to read this:</strong> Warmer colours (red/orange) indicate areas the model identified as having 
          <strong> compression anomalies or blending artifacts</strong> — common signatures of AI-generated or manipulated media.
        </p>
      </div>
    </motion.div>
  );
};

export default HeatmapViewer;
