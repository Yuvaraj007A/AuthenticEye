import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  ShieldCheck, ShieldX, BrainCircuit, Fingerprint, Sparkles, 
  Radio, Clock, Zap, FileText, AlertTriangle, Cpu, HelpCircle 
} from 'lucide-react';
import api from '../services/api';

const ScoreBar = ({ label, value, icon: Icon, color, delay = 0, type }) => {
  let valStr = '';
  let badgeClass = '';

  if (type === 'c2pa') {
    if (value === 0.5 || value === undefined || value === null) {
      valStr = 'Not Detected';
      badgeClass = 'bg-slate-50 text-slate-400 border border-slate-100';
    } else if (value < 0.5) {
      valStr = 'Verified Authentic';
      badgeClass = 'bg-emerald-50 text-emerald-600 border border-emerald-100';
    } else {
      valStr = 'Tampered / Synthetic';
      badgeClass = 'bg-rose-50 text-rose-600 border border-rose-100';
    }
  } else {
    const isPercent = typeof value === 'number';
    const isTrueFake = isPercent ? value > 0.5 : !!value;
    valStr = isTrueFake ? 'Fake' : 'Real';
    badgeClass = isTrueFake 
      ? 'bg-rose-50 text-rose-600 border border-rose-100' 
      : 'bg-emerald-50 text-emerald-600 border border-emerald-100';
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="space-y-1.5 py-3 border-b border-slate-100 last:border-0"
    >
      <div className="flex justify-between items-center text-xs">
        <div className="flex items-center gap-2 text-slate-600 font-semibold">
          <Icon size={14} className={color} />
          <span>{label}</span>
        </div>
        <span className={`font-black px-2 py-0.5 rounded text-[10px] uppercase ${badgeClass}`}>
          {valStr}
        </span>
      </div>
    </motion.div>
  );
};

const ResultCard = ({ result, imageUrl }) => {
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [loadingFeedback, setLoadingFeedback] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [activeTab, setActiveTab] = useState('original');

  if (!result) return null;

  const handleFeedbackSubmit = async (userLabel) => {
    setLoadingFeedback(true);
    try {
      await api.post('/feedback', {
        analysisId: result._id,
        userLabel,
      });
      setFeedbackSubmitted(true);
      setFeedbackMsg('Thank you! Your feedback has been submitted to the admin queue for verification.');
    } catch (err) {
      console.error('Feedback submission failed:', err);
      setFeedbackMsg('Failed to submit feedback. Please try again.');
      setFeedbackSubmitted(true);
    } finally {
      setLoadingFeedback(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const res = await api.get(`/history/${result._id}/report`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `AuthenticEye_Report_${result._id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF report.');
    }
  };

  const mediaType = result.mediaType || 'image';
  const ai = result.aiDetail || {};
  
  // Resolve unified fields
  const finalPrediction = result.prediction ?? ai.prediction ?? (result.deepfakeProbability > 0.5 ? 'AI_GENERATED' : 'REAL');
  const isFake = finalPrediction === 'AI_GENERATED';
  const confidence = result.confidence ?? ai.confidence ?? 0.50;
  const riskLevel = result.riskLevel ?? ai.risk_level ?? (isFake ? 'HIGH' : 'LOW');
  const analysisTime = result.analysisTimeSeconds || 'N/A';
  
  // Extract explanations
  const explanation = result.explanation ?? ai.explanation ?? {};
  const reasons = explanation.reasons ?? [];
  const explanationSummary = explanation.summary ?? '';

  // Extract raw scores
  const scores = result.scores ?? ai.scores ?? {};
  
  // Mapping display configurations
  const DETECTORS_META = [
    { key: 'efficientnet', label: 'EfficientNet-B4 (DFDC)', icon: BrainCircuit, color: 'text-teal-500' },
    { key: 'xception', label: 'XceptionNet (FF++)', icon: BrainCircuit, color: 'text-blue-500' },
    { key: 'frequency', label: 'Frequency Forensics (FFT/DCT)', icon: Radio, color: 'text-amber-500' },
    { key: 'synthid', label: 'SynthID Watermark', icon: Fingerprint, color: 'text-rose-500' },
    { key: 'metadata', label: 'Metadata Forensics (EXIF)', icon: Sparkles, color: 'text-fuchsia-500' },
    { key: 'c2pa', label: 'C2PA Content Credentials', icon: ShieldCheck, color: 'text-emerald-500', type: 'c2pa' }
  ];

  const VIDEO_META = [
    { key: 'avg_frame_ensemble', label: 'Average Frame Ensemble', icon: BrainCircuit, color: 'text-teal-500' },
    { key: 'temporal_consistency', label: 'Temporal Consistency (LSTM)', icon: Clock, color: 'text-violet-500' },
    { key: 'optical_flow_deviation', label: 'Optical Flow Jitter', icon: Radio, color: 'text-amber-500' },
    { key: 'embedding_drift', label: 'Embedding Identity Drift', icon: Sparkles, color: 'text-fuchsia-500' }
  ];

  const getStaticUrl = (subPath) => {
    if (!subPath) return '';
    return subPath;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"
    >
      {/* ─── Verdict Banner ─── */}
      <div className={`px-6 py-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b ${
        isFake 
          ? 'bg-gradient-to-r from-rose-50 to-orange-50/50 border-rose-100' 
          : 'bg-gradient-to-r from-emerald-50 to-teal-50/50 border-emerald-100'
      }`}>
        <div className="flex items-center gap-4">
          {isFake 
            ? <ShieldX size={44} className="text-rose-500 flex-shrink-0 drop-shadow-sm" /> 
            : <ShieldCheck size={44} className="text-emerald-500 flex-shrink-0 drop-shadow-sm" />
          }
          <div>
            <p className="text-[10px] uppercase tracking-widest font-black text-slate-500">
              {mediaType.toUpperCase()} CLASSIFICATION
            </p>
            <h2 className={`text-3xl font-black mt-0.5 tracking-tight ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
              {isFake ? 'SYNTHETIC / AI FAKE' : 'AUTHENTIC / REAL'}
            </h2>
          </div>
        </div>
        
        {/* Actions (PDF download / Analysis Time) */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-[10px] font-black px-3 py-1.5 rounded-full uppercase tracking-wider ${
            riskLevel === 'HIGH' 
              ? 'bg-rose-100 text-rose-700 border border-rose-200' 
              : riskLevel === 'MEDIUM' 
              ? 'bg-amber-100 text-amber-700 border border-amber-200'
              : 'bg-emerald-100 text-emerald-700 border border-emerald-200'
          }`}>
            {riskLevel} RISK LEVEL
          </span>

          <button
            onClick={handleDownloadPDF}
            className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 rounded-xl transition shadow-sm"
          >
            <FileText size={15} className="text-indigo-600" />
            PDF Report
          </button>

          {analysisTime !== 'N/A' && (
            <div className="flex items-center gap-2.5 bg-white/80 px-3.5 py-1.5 rounded-xl border border-slate-200 shadow-sm">
              <Zap size={14} className="text-amber-500 fill-amber-500" />
              <span className="text-xs font-bold text-slate-700">{analysisTime}s</span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 md:p-8">
        <div className="grid md:grid-cols-2 gap-8">

          {/* ─── LEFT: Visual Comparison Area ─── */}
          <div className="space-y-6">
            {mediaType === 'image' ? (
              <div className="space-y-3">
                {/* Visual tabs */}
                <div className="flex gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
                  {['original', 'gradcam', 'fft', 'artifact'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`flex-1 py-1.5 text-center text-xs font-bold rounded-lg capitalize transition ${
                        activeTab === tab ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      {tab === 'fft' ? 'FFT' : tab === 'gradcam' ? 'Grad-CAM' : tab}
                    </button>
                  ))}
                </div>

                {/* Display Area */}
                <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-50 flex items-center justify-center max-h-64 aspect-video shadow-inner">
                  {activeTab === 'original' && imageUrl && (
                    <img src={imageUrl} alt="Original" className="w-full h-full object-contain" />
                  )}
                  {activeTab === 'gradcam' && (
                    <img 
                      src={
                        result.explanationAssets?.gradcamUrl 
                          ? getStaticUrl(result.explanationAssets.gradcamUrl)
                          : (result.heatmapBase64 ? `data:image/jpeg;base64,${result.heatmapBase64}` : (ai.heatmap_base64 ? `data:image/jpeg;base64,${ai.heatmap_base64}` : ''))
                      } 
                      alt="Grad-CAM" 
                      className="w-full h-full object-contain" 
                    />
                  )}
                  {activeTab === 'fft' && (
                    <img 
                      src={
                        result.explanationAssets?.fftUrl 
                          ? getStaticUrl(result.explanationAssets.fftUrl)
                          : (ai.fft_base64 ? `data:image/jpeg;base64,${ai.fft_base64}` : '')
                      } 
                      alt="FFT Spectrum" 
                      className="w-full h-full object-contain" 
                    />
                  )}
                  {activeTab === 'artifact' && (
                    <img 
                      src={
                        result.explanationAssets?.ganUrl 
                          ? getStaticUrl(result.explanationAssets.ganUrl)
                          : (ai.gan_base64 ? `data:image/jpeg;base64,${ai.gan_base64}` : '')
                      } 
                      alt="Artifacts" 
                      className="w-full h-full object-contain" 
                    />
                  )}
                  
                  {/* Scanner overlay effect */}
                  <motion.div
                    initial={{ top: '0%' }}
                    animate={{ top: '100%' }}
                    transition={{ duration: 2.5, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
                    className={`absolute left-0 w-full h-0.5 ${isFake ? 'bg-rose-400 shadow-[0_0_10px_rgba(239,68,68,0.8)]' : 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]'}`}
                  />
                </div>
              </div>
            ) : (
              imageUrl && (
                <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-50 shadow-inner">
                  <img src={imageUrl} alt="Analyzed" className="w-full max-h-64 object-contain" />
                  <motion.div
                    initial={{ top: '0%' }}
                    animate={{ top: '100%' }}
                    transition={{ duration: 2.5, repeat: Infinity, repeatType: 'reverse', ease: 'linear' }}
                    className={`absolute left-0 w-full h-0.5 ${isFake ? 'bg-rose-400 shadow-[0_0_10px_rgba(239,68,68,0.8)]' : 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]'}`}
                  />
                </div>
              )
            )}

            {/* Explainability reasons list */}
            {reasons.length > 0 && (
              <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 shadow-sm space-y-3 text-left">
                <p className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <HelpCircle size={14} className="text-indigo-500" />
                  Forensic Findings Summary
                </p>
                <p className="text-xs text-slate-600 font-semibold leading-relaxed mb-2">
                  {explanationSummary}
                </p>
                <div className="space-y-2.5">
                  {reasons.map((reason, idx) => (
                    <div key={idx} className="flex gap-2.5 items-start text-xs text-slate-700">
                      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${isFake ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                      <p className="leading-normal font-medium">{reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ─── RIGHT: Per-detector score registry charts ─── */}
          <div className="space-y-6 text-left">
            
            {/* Core Gauge Card */}
            <div className={`p-6 rounded-2xl border ${
              isFake 
                ? 'border-rose-100 bg-gradient-to-br from-rose-50/20 to-orange-50/10' 
                : 'border-emerald-100 bg-gradient-to-br from-emerald-50/20 to-teal-50/10'
            } text-center flex flex-col items-center justify-center shadow-sm relative overflow-hidden`}>
              
              <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-bl-full pointer-events-none" />
              
              <div className={`w-14 h-14 rounded-full flex items-center justify-center mb-3 shadow-md ${
                isFake ? 'bg-rose-100 text-rose-600 border border-rose-200' : 'bg-emerald-100 text-emerald-600 border border-emerald-200'
              }`}>
                {isFake ? <ShieldX size={26} /> : <ShieldCheck size={26} />}
              </div>
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Verdict</p>
              <p className={`text-4xl font-black mt-1 ${isFake ? 'text-rose-600' : 'text-emerald-700'}`}>
                {isFake ? 'Fake' : 'Real'}
              </p>
            </div>

            {/* C2PA Detailed Metadata Box */}
            {scores.c2pa_detected && (
              <div className={`p-5 rounded-2xl border ${
                scores.c2pa_valid 
                  ? 'border-emerald-100 bg-emerald-50/10' 
                  : 'border-rose-100 bg-rose-50/10'
              } shadow-sm space-y-3`}>
                <div className="flex items-center gap-2">
                  <ShieldCheck size={16} className={scores.c2pa_valid ? 'text-emerald-600' : 'text-rose-600'} />
                  <p className={`text-xs font-black uppercase tracking-wider ${
                    scores.c2pa_valid ? 'text-emerald-700' : 'text-rose-700'
                  }`}>
                    Content Credentials (C2PA)
                  </p>
                </div>
                <p className="text-xs text-slate-600 leading-normal">
                  {scores.c2pa_valid ? (
                    "This image contains a valid cryptographic signature and matches its recorded provenance chain."
                  ) : (
                    "Warning: The cryptographic signature is invalid or tampered, indicating the file was altered since signing."
                  )}
                </p>
                
                {scores.c2pa_info && (
                  <div className="p-3 bg-white/80 border border-slate-100 rounded-xl space-y-2 text-[11px] text-slate-600">
                    {scores.c2pa_info.claim_generator && (
                      <div>
                        <span className="font-bold text-slate-500">Claim Generator:</span>{' '}
                        {scores.c2pa_info.claim_generator}
                      </div>
                    )}
                    
                    {(() => {
                      const manifests = scores.c2pa_info.manifests || {};
                      const activeId = scores.c2pa_info.active_manifest;
                      if (activeId && manifests[activeId]) {
                        const active = manifests[activeId];
                        const signatureInfo = active.signature_info || {};
                        const issuer = signatureInfo.issuer || signatureInfo.authority;
                        const time = signatureInfo.time;
                        return (
                          <>
                            {issuer && (
                              <div>
                                <span className="font-bold text-slate-500">Signed By:</span>{' '}
                                {issuer}
                              </div>
                            )}
                            {time && (
                              <div>
                                <span className="font-bold text-slate-500">Date Signed:</span>{' '}
                                {new Date(time).toLocaleString()}
                              </div>
                            )}
                          </>
                        );
                      }
                      return null;
                    })()}
                  </div>
                )}
              </div>
            )}

            {/* Detector Registry Scores */}
            {Object.keys(scores).length > 0 && (
              <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <BrainCircuit size={16} className="text-violet-500" />
                  <p className="text-xs font-black uppercase tracking-wider text-violet-600">
                    {mediaType === 'image' ? '8-Detector Ensemble Registry Breakdown' : 'Temporal Video Analysis Breakdown'}
                  </p>
                </div>
                
                <div className="flex flex-col">
                  {mediaType === 'image' ? (
                    DETECTORS_META.map((meta, i) => {
                      const val = scores[meta.key];
                      if (val === undefined) return null;
                      return (
                        <ScoreBar
                          key={meta.key}
                          label={meta.label}
                          value={val}
                          icon={meta.icon}
                          color={meta.color}
                          delay={i * 0.05}
                          type={meta.type}
                        />
                      );
                    })
                  ) : (
                    VIDEO_META.map((meta, i) => {
                      const val = scores[meta.key];
                      if (val === undefined) return null;
                      return (
                        <ScoreBar
                          key={meta.key}
                          label={meta.label}
                          value={val}
                          icon={meta.icon}
                          color={meta.color}
                          delay={i * 0.05}
                        />
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Video frame status metrics */}
            {ai.frames_analyzed && (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 shadow-sm">
                  <p className="font-black text-slate-800 text-xl">{ai.frames_analyzed}</p>
                  <p className="text-[10px] uppercase font-bold text-slate-400 mt-1">Frames</p>
                </div>
                <div className="p-4 bg-rose-50 rounded-xl border border-rose-100 shadow-sm">
                  <p className="font-black text-rose-700 text-xl">{result.flagged_frames ?? ai.flagged_frames ?? 'N/A'}</p>
                  <p className="text-[10px] uppercase font-bold text-rose-400 mt-1">Flagged</p>
                </div>
                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 shadow-sm">
                  <p className="font-black text-emerald-700 text-xl">{ai.faces_detected_in ?? 'N/A'}</p>
                  <p className="text-[10px] uppercase font-bold text-emerald-400 mt-1">Faces</p>
                </div>
              </div>
            )}

            {/* Feedback Submission */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-3">
                Help Improve Detection Accuracy
              </p>
              {!feedbackSubmitted ? (
                <div className="flex flex-col sm:flex-row gap-3">
                  <span className="text-slate-500 text-xs self-center">Is this prediction incorrect? Flag as:</span>
                  <div className="flex gap-2 ml-auto">
                    <button
                      onClick={() => handleFeedbackSubmit('real')}
                      disabled={loadingFeedback}
                      className="px-4 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold border border-emerald-200 transition-colors"
                    >
                      Correct Label: Real
                    </button>
                    <button
                      onClick={() => handleFeedbackSubmit('fake')}
                      disabled={loadingFeedback}
                      className="px-4 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg text-xs font-bold border border-rose-200 transition-colors"
                    >
                      Correct Label: Fake
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-center">
                  <p className="text-xs font-bold text-indigo-700">{feedbackMsg}</p>
                </div>
              )}
            </div>

          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;
