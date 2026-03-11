import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldX, BrainCircuit, Fingerprint, Sparkles, Radio, Clock } from 'lucide-react';

// ─── Sub-components ───────────────────────────────────────────────────────────

const ConfidenceMeter = ({ value, isFake }) => {
  const pct = Math.round(value * 100);
  return (
    <div className="relative w-36 h-36 mx-auto">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle cx="60" cy="60" r="50" fill="none" stroke="#f1f5f9" strokeWidth="12" />
        <motion.circle
          cx="60" cy="60" r="50" fill="none"
          stroke={isFake ? '#f43f5e' : '#10b981'}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${2 * Math.PI * 50}`}
          initial={{ strokeDashoffset: 2 * Math.PI * 50 }}
          animate={{ strokeDashoffset: 2 * Math.PI * 50 * (1 - value) }}
          transition={{ duration: 1.4, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-black ${isFake ? 'text-rose-600' : 'text-emerald-600'}`}>
          {pct}%
        </span>
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
          {isFake ? 'Fake' : 'Real'}
        </span>
      </div>
    </div>
  );
};

const ScoreRow = ({ label, value, icon: Icon, color, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, x: -10 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay, duration: 0.3 }}
    className="space-y-1"
  >
    <div className="flex justify-between items-center text-xs">
      <div className="flex items-center gap-1.5 text-slate-600">
        <Icon size={12} className={color} />
        <span className="font-medium">{label}</span>
      </div>
      <span className={`font-bold text-xs ${parseFloat(value) > 50 ? 'text-rose-600' : 'text-emerald-600'}`}>
        {typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : value}
      </span>
    </div>
    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(typeof value === 'number' ? value * 100 : 0, 100)}%` }}
        transition={{ delay, duration: 0.8, ease: 'easeOut' }}
        className={`h-1.5 rounded-full ${(typeof value === 'number' ? value : 0) > 0.5 ? 'bg-rose-400' : 'bg-emerald-400'}`}
      />
    </div>
  </motion.div>
);

// ─── Main ResultCard ───────────────────────────────────────────────────────────

const ResultCard = ({ result, imageUrl }) => {
  if (!result) return null;

  const prob = result.deepfakeProbability ?? result.deepfake_probability ?? 0;
  const auth = result.authenticityScore ?? result.authenticity_score ?? 0;
  const isFake = prob > 0.5;
  const mediaType = result.mediaType || 'image';
  const ai = result.aiDetail || {};

  const modelScores = ai.model_scores || result.modelScores || {};
  const ganProb = ai.gan_probability ?? result.ganProbability ?? 0;
  const diffProb = ai.diffusion_probability ?? result.diffusionProbability ?? 0;
  const temporalScore = ai.temporal_score ?? null;
  const temporalDrift = ai.temporal_drift ?? null;

  const MODEL_META = [
    { key: 'efficientnet_b4', label: 'EfficientNet-B4', icon: BrainCircuit, color: 'text-violet-500' },
    { key: 'xceptionnet', label: 'XceptionNet', icon: BrainCircuit, color: 'text-blue-500' },
    { key: 'vision_transformer', label: 'Vision Transformer', icon: BrainCircuit, color: 'text-indigo-500' },
    { key: 'frequency_cnn', label: 'Frequency CNN', icon: Radio, color: 'text-amber-500' },
    { key: 'gan_fingerprint', label: 'GAN Fingerprint', icon: Fingerprint, color: 'text-rose-500' },
    { key: 'diffusion_detector', label: 'Diffusion Detector', icon: Sparkles, color: 'text-fuchsia-500' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"
    >
      {/* ─── Verdict Banner ─── */}
      <div className={`px-6 py-4 flex items-center gap-4 ${isFake ? 'bg-rose-50 border-b border-rose-100' : 'bg-emerald-50 border-b border-emerald-100'}`}>
        {isFake ? <ShieldX size={32} className="text-rose-500 flex-shrink-0" /> : <ShieldCheck size={32} className="text-emerald-500 flex-shrink-0" />}
        <div>
          <p className="text-xs uppercase tracking-widest font-bold text-slate-400">
            {mediaType.toUpperCase()} FORENSIC VERDICT
          </p>
          <h2 className={`text-2xl font-black ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
            {isFake ? '⚠️ MANIPULATED MEDIA DETECTED' : '✅ AUTHENTIC MEDIA'}
          </h2>
        </div>
      </div>

      <div className="p-6 md:p-8">
        <div className="grid md:grid-cols-2 gap-8">

          {/* ─── LEFT: Image + Confidence Meter ─── */}
          <div className="space-y-6">
            {imageUrl && (
              <div className="relative rounded-xl overflow-hidden border border-slate-100 bg-slate-50">
                <img src={imageUrl} alt="Analyzed" className="w-full max-h-56 object-contain" />
                <motion.div
                  initial={{ top: '0%' }}
                  animate={{ top: '100%' }}
                  transition={{ duration: 2.5, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
                  className={`absolute left-0 w-full h-0.5 ${isFake ? 'bg-rose-400 shadow-[0_0_10px_rgba(239,68,68,0.8)]' : 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]'}`}
                />
              </div>
            )}

            {/* Confidence Meter */}
            <div className="text-center">
              <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-3">
                Confidence Meter
              </p>
              <ConfidenceMeter value={isFake ? prob : auth} isFake={isFake} />
            </div>

            {/* Specialized scores for image */}
            {mediaType === 'image' && (
              <div className="space-y-2 pt-2">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Specialized Analysis</p>
                <ScoreRow label="GAN Fingerprint Probability" value={ganProb} icon={Fingerprint} color="text-rose-500" delay={0.1} />
                <ScoreRow label="Diffusion Model Probability" value={diffProb} icon={Sparkles} color="text-fuchsia-500" delay={0.2} />
              </div>
            )}

            {/* Video temporal stats */}
            {mediaType === 'video' && temporalScore !== null && (
              <div className="space-y-2 pt-2">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Temporal Analysis</p>
                <ScoreRow label="Temporal Inconsistency" value={temporalScore} icon={Clock} color="text-violet-500" delay={0.1} />
                <ScoreRow label="Feature Drift Score" value={temporalDrift ?? 0} icon={Radio} color="text-amber-500" delay={0.2} />
              </div>
            )}
          </div>

          {/* ─── RIGHT: Per-model scores ─── */}
          <div className="space-y-5">
            {/* Model breakdown */}
            {Object.keys(modelScores).length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <BrainCircuit size={16} className="text-violet-500" />
                  <p className="text-xs font-bold uppercase tracking-wider text-violet-600">
                    6-Module Ensemble Breakdown
                  </p>
                </div>
                <div className="space-y-3">
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

            {/* Authenticity Score */}
            <div className={`p-4 rounded-xl border ${isFake ? 'border-rose-100 bg-rose-50/50' : 'border-emerald-100 bg-emerald-50/50'}`}>
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Authenticity Score</p>
                  <p className={`text-3xl font-black mt-1 ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
                    {(auth * 100).toFixed(1)}%
                  </p>
                </div>
                <div className={`text-5xl`}>{isFake ? '🔴' : '🟢'}</div>
              </div>
            </div>

            {/* Video frame stats */}
            {ai.frames_analyzed && (
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="font-bold text-slate-800 text-lg">{ai.frames_analyzed}</p>
                  <p className="text-xs text-slate-400">Frames</p>
                </div>
                <div className="p-3 bg-rose-50 rounded-xl border border-rose-100">
                  <p className="font-bold text-rose-700 text-lg">{ai.flagged_frames}</p>
                  <p className="text-xs text-rose-400">Flagged</p>
                </div>
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                  <p className="font-bold text-emerald-700 text-lg">{ai.faces_detected_in}</p>
                  <p className="text-xs text-emerald-400">Faces</p>
                </div>
              </div>
            )}

            {/* Audit trail */}
            <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl text-xs text-slate-500 italic leading-relaxed">
              <strong>Forensic Engine v5.0:</strong> Ensemble of EfficientNet-B4 (30%) + XceptionNet (25%) + ViT (20%) +
              Frequency CNN (10%) + GAN Fingerprint (10%) + Diffusion Detector (5%).{' '}
              {mediaType === 'image' && 'Face aligned via MediaPipe 468-pt landmarks. Grad-CAM heatmap available below.'}
              {mediaType === 'video' && 'Temporal LSTM models inter-frame inconsistency across extracted frames.'}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;
