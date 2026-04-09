import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldX, BrainCircuit, Fingerprint, Sparkles, Radio, Clock, Zap } from 'lucide-react';

const ScoreRow = ({ label, value, icon: Icon, color, delay = 0 }) => {
  const isHigh = typeof value === 'number' && value > 0.5;
  const statusText = typeof value === 'number' ? (isHigh ? 'High Risk' : 'Normal') : value;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="flex justify-between items-center py-2.5 border-b border-slate-100 last:border-0"
    >
      <div className="flex items-center gap-2.5 text-slate-600">
        <Icon size={16} className={color} />
        <span className="font-medium text-sm">{label}</span>
      </div>
      <span className={`font-bold text-xs px-2.5 py-1 rounded-md ${isHigh ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
        {statusText}
      </span>
    </motion.div>
  );
};

// ─── Main ResultCard ───────────────────────────────────────────────────────────

const ResultCard = ({ result, imageUrl }) => {
  if (!result) return null;

  const prob = result.deepfakeProbability ?? result.deepfake_probability ?? 0;
  const isFake = prob > 0.5;
  const analysisTime = result.analysisTimeSeconds || 'N/A';
  const mediaType = result.mediaType || 'image';
  const ai = result.aiDetail || {};

  const modelScores = ai.model_scores || result.modelScores || result.model_scores || {};
  const ganProb = ai.gan_probability ?? result.ganProbability ?? result.gan_probability ?? 0;
  const diffProb = ai.diffusion_probability ?? result.diffusionProbability ?? result.diffusion_probability ?? 0;
  const temporalScore = ai.temporal_score ?? null;
  const temporalDrift = ai.temporal_drift ?? null;

  const MODEL_META = [
    { key: 'efficientnet_b4', label: 'EfficientNet-B4', icon: BrainCircuit, color: 'text-violet-500' },
    { key: 'xceptionnet', label: 'XceptionNet', icon: BrainCircuit, color: 'text-blue-500' },
    { key: 'vision_transformer', label: 'Vision Transformer', icon: BrainCircuit, color: 'text-indigo-500' },
    { key: 'frequency_cnn', label: 'Frequency Array', icon: Radio, color: 'text-amber-500' },
    { key: 'gan_fingerprint', label: 'GAN Fingerprint', icon: Fingerprint, color: 'text-rose-500' },
    { key: 'diffusion_detector', label: 'Diffusion Traces', icon: Sparkles, color: 'text-fuchsia-500' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"
    >
      {/* ─── Verdict Banner ─── */}
      <div className={`px-6 py-5 flex flex-col md:flex-row md:items-center justify-between gap-4 ${isFake ? 'bg-rose-50 border-b border-rose-100' : 'bg-emerald-50 border-b border-emerald-100'}`}>
        <div className="flex items-center gap-4">
          {isFake ? <ShieldX size={40} className="text-rose-500 flex-shrink-0" /> : <ShieldCheck size={40} className="text-emerald-500 flex-shrink-0" />}
          <div>
            <p className="text-xs uppercase tracking-widest font-bold text-slate-500">
              {mediaType.toUpperCase()} ANALYSIS RESULT
            </p>
            <h2 className={`text-3xl font-black mt-1 ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
              {isFake ? 'FAKE' : 'REAL'}
            </h2>
          </div>
        </div>
        
        {/* Analysis Time */}
        {analysisTime !== 'N/A' && (
          <div className="flex items-center gap-3 bg-white/60 px-4 py-2.5 rounded-xl backdrop-blur-sm border border-white">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Zap size={20} className="text-amber-600" />
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Analysis Time</p>
              <p className="text-sm font-black text-slate-800">{analysisTime} Seconds</p>
            </div>
          </div>
        )}
      </div>

      <div className="p-6 md:p-8">
        <div className="grid md:grid-cols-2 gap-8">

          {/* ─── LEFT: Image & Core Stats ─── */}
          <div className="space-y-6">
            {imageUrl && (
              <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-50">
                <img src={imageUrl} alt="Analyzed" className="w-full max-h-64 object-contain" />
                <motion.div
                  initial={{ top: '0%' }}
                  animate={{ top: '100%' }}
                  transition={{ duration: 2.5, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
                  className={`absolute left-0 w-full h-0.5 ${isFake ? 'bg-rose-400 shadow-[0_0_10px_rgba(239,68,68,0.8)]' : 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]'}`}
                />
              </div>
            )}

            {/* Specialized scores for image */}
            {mediaType === 'image' && (
              <div className="space-y-2 bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Specialized Analysis</p>
                <ScoreRow label="GAN Fingerprint" value={ganProb} icon={Fingerprint} color="text-rose-500" delay={0.1} />
                <ScoreRow label="Diffusion Model Traces" value={diffProb} icon={Sparkles} color="text-fuchsia-500" delay={0.2} />
              </div>
            )}

            {/* Video temporal stats */}
            {mediaType === 'video' && temporalScore !== null && (
              <div className="space-y-2 bg-slate-50 p-4 rounded-xl border border-slate-100">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Temporal Analysis</p>
                <ScoreRow label="Temporal Inconsistency" value={temporalScore} icon={Clock} color="text-violet-500" delay={0.1} />
                <ScoreRow label="Feature Drift Status" value={temporalDrift ?? 0} icon={Radio} color="text-amber-500" delay={0.2} />
              </div>
            )}
          </div>

          {/* ─── RIGHT: Per-model scores ─── */}
          <div className="space-y-6">
            
            {/* Final Verdict Banner - Replaces the old percentages */}
            <div className={`p-6 rounded-2xl border ${isFake ? 'border-rose-200 bg-rose-50/50' : 'border-emerald-200 bg-emerald-50/50'} text-center flex flex-col items-center justify-center`}>
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-sm ${isFake ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'}`}>
                {isFake ? <ShieldX size={32} /> : <ShieldCheck size={32} />}
              </div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-2">Final Conclusion</p>
              <p className={`text-2xl font-black ${isFake ? 'text-rose-700' : 'text-emerald-700'}`}>
                {isFake ? 'Synthetically Generated' : 'Authentic Media'}
              </p>
            </div>

            {/* Model breakdown */}
            {Object.keys(modelScores).length > 0 && (
              <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <BrainCircuit size={16} className="text-violet-500" />
                  <p className="text-xs font-bold uppercase tracking-wider text-violet-600">
                    6-Module Ensemble Breakdown
                  </p>
                </div>
                <div className="flex flex-col">
                  {MODEL_META.map((m, i) => {
                    const val = modelScores[m.key];
                    if (val === undefined) return null;
                    return (
                      <ScoreRow
                        key={m.key}
                        label={m.label}
                        value={val}
                        icon={m.icon}
                        color={m.color}
                        delay={i * 0.05}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {/* Video frame stats */}
            {ai.frames_analyzed && (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 shadow-sm">
                  <p className="font-black text-slate-800 text-xl">{ai.frames_analyzed}</p>
                  <p className="text-[10px] uppercase font-bold text-slate-400 mt-1">Frames</p>
                </div>
                <div className="p-4 bg-rose-50 rounded-xl border border-rose-100 shadow-sm">
                  <p className="font-black text-rose-700 text-xl">{ai.flagged_frames}</p>
                  <p className="text-[10px] uppercase font-bold text-rose-400 mt-1">Flagged</p>
                </div>
                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 shadow-sm">
                  <p className="font-black text-emerald-700 text-xl">{ai.faces_detected_in}</p>
                  <p className="text-[10px] uppercase font-bold text-emerald-400 mt-1">Faces</p>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;
