import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, ShieldX, BrainCircuit, Play, History, RotateCcw, 
  CheckCircle, XCircle, RefreshCw, Layers, FileText, AlertTriangle,
  Server, Activity, Users, Cpu
} from 'lucide-react';
import api from '../services/api';

const AdminDashboard = () => {
  const [feedbackList, setFeedbackList] = useState([]);
  const [modelList, setModelList] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [actionMsg, setActionMsg] = useState('');

  // Fetch all admin data
  const fetchData = async () => {
    try {
      const [fbRes, modelRes, logRes, analyticsRes] = await Promise.all([
        api.get('/admin/feedback'),
        api.get('/admin/models'),
        api.get('/admin/audit-logs'),
        api.get('/admin/analytics').catch(err => {
          console.error("Failed to fetch analytics:", err);
          return { data: null };
        })
      ]);
      setFeedbackList(fbRes.data);
      setModelList(modelRes.data);
      setAuditLogs(logRes.data);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      console.error('Error fetching admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handle Feedback Verification
  const handleVerify = async (feedbackId, status, verifiedLabel) => {
    try {
      setActionMsg('Processing verification...');
      await api.post('/admin/feedback/verify', { feedbackId, status, verifiedLabel });
      setActionMsg(`Feedback ${status} successfully.`);
      fetchData();
    } catch (err) {
      console.error('Verification error:', err);
      setActionMsg('Verification action failed.');
    }
  };

  // Trigger Retraining
  const handleRetrain = async () => {
    setRetraining(true);
    setActionMsg('Automated model retraining started in background (this may take up to 10 minutes on CPU)...');
    try {
      const res = await api.post('/admin/retrain');
      setActionMsg(`Retraining finished successfully! New version ${res.data.modelVersion.version} promoted to active.`);
      fetchData();
    } catch (err) {
      console.error('Retraining error:', err);
      setActionMsg('Retraining failed. Please inspect logs.');
    } finally {
      setRetraining(false);
    }
  };

  // Handle Rollback
  const handleRollback = async (version) => {
    try {
      setActionMsg(`Rolling back active model to version ${version}...`);
      await api.post('/admin/models/rollback', { version });
      setActionMsg(`Successfully rolled back to version ${version}.`);
      fetchData();
    } catch (err) {
      console.error('Rollback error:', err);
      setActionMsg('Rollback failed.');
    }
  };

  // Count pending un-retrained verified samples
  const pendingRetrainCount = feedbackList.filter(
    (fb) => fb.status === 'verified' && !fb.isUsedInRetraining
  ).length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="animate-spin text-indigo-500" size={40} />
          <p className="font-bold text-sm tracking-wider uppercase text-slate-400">Loading Admin Control Panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6 md:p-12 font-sans selection:bg-indigo-500 selection:text-white">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-white flex items-center gap-3">
              <BrainCircuit className="text-indigo-500" size={32} />
              Feedback-Driven Adaptive Learning System
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Verify user correction inputs, initiate background model retraining, and manage version registries.
            </p>
          </div>
          <button
            onClick={handleRetrain}
            disabled={retraining || pendingRetrainCount === 0}
            className={`flex items-center gap-2.5 px-6 py-3 rounded-xl font-bold text-sm shadow-md transition-all ${
              retraining || pendingRetrainCount === 0 
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700' 
                : 'bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-400/20 active:scale-95'
            }`}
          >
            {retraining ? (
              <RefreshCw className="animate-spin" size={16} />
            ) : (
              <Play size={16} />
            )}
            Trigger Automated Retraining ({pendingRetrainCount} pending verified)
          </button>
        </div>

        {/* Action / Notification Message Banner */}
        <AnimatePresence>
          {actionMsg && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-indigo-950/40 border border-indigo-500/30 p-4 rounded-xl flex items-center justify-between text-indigo-300 text-xs font-bold"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-indigo-400" />
                <span>{actionMsg}</span>
              </div>
              <button onClick={() => setActionMsg('')} className="text-indigo-400 hover:text-white">Dismiss</button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Analytics & System Health Overview Grid */}
        {analytics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* Card 1: System Health */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl flex items-center justify-between shadow-lg relative overflow-hidden backdrop-blur-md">
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-400 tracking-wider uppercase">System Health</p>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-sm">
                    <span className="text-slate-500 font-medium">Database:</span>
                    <span className={`flex items-center gap-1 font-bold ${analytics.system.database === 'healthy' ? 'text-emerald-400' : 'text-rose-400'}`}>
                      <span className={`w-2 h-2 rounded-full ${analytics.system.database === 'healthy' ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`} />
                      {analytics.system.database.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
              <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
                <Server size={22} />
              </div>
            </div>

            {/* Card 2: Model Status */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl flex items-center justify-between shadow-lg relative overflow-hidden backdrop-blur-md">
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 tracking-wider uppercase">Active Model</p>
                <p className="text-2xl font-black text-white">{analytics.ai.activeModelVersion}</p>
                {analytics.ai.activeModelMetrics ? (
                  <p className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                    Acc: {(analytics.ai.activeModelMetrics.accuracy * 100).toFixed(1)}% | F1: {(analytics.ai.activeModelMetrics.f1 * 100).toFixed(1)}%
                  </p>
                ) : (
                  <p className="text-[10px] text-slate-500 font-semibold">Standard Ensemble Weights</p>
                )}
              </div>
              <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                <Cpu size={22} />
              </div>
            </div>

            {/* Card 3: AI Detections */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl flex items-center justify-between shadow-lg relative overflow-hidden backdrop-blur-md">
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 tracking-wider uppercase">Detections Run</p>
                <p className="text-2xl font-black text-white">{analytics.ai.totalDetections}</p>
                <p className="text-[10px] text-slate-500 font-semibold">
                  Images: {analytics.ai.imagesCount} | Videos: {analytics.ai.videosCount}
                </p>
              </div>
              <div className="p-3 bg-violet-500/10 text-violet-400 rounded-xl border border-violet-500/20">
                <Activity size={22} />
              </div>
            </div>

            {/* Card 4: Detections Summary */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl flex items-center justify-between shadow-lg relative overflow-hidden backdrop-blur-md">
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-400 tracking-wider uppercase">Scanning Metrics</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    Fake: {analytics.ai.fakesCount}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Real: {analytics.ai.realsCount}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 font-semibold">
                  Avg Confidence: {(analytics.ai.avgConfidence * 100).toFixed(1)}%
                </p>
              </div>
              <div className="p-3 bg-pink-500/10 text-pink-400 rounded-xl border border-pink-500/20">
                <Users size={22} />
              </div>
            </div>

          </div>
        )}

        {/* Grid Layout */}
        <div className="grid lg:grid-cols-3 gap-8">

          {/* Left/Middle Column: Verification List & Version Control */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Feedback Queue */}
            <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
              <h2 className="text-xl font-black mb-4 flex items-center gap-2">
                <Layers className="text-indigo-500" size={20} />
                User Feedback Queue
              </h2>
              <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                {feedbackList.filter(f => f.status === 'pending').length === 0 ? (
                  <p className="text-slate-500 text-xs text-center py-8">No pending user corrections awaiting verification.</p>
                ) : (
                  feedbackList.filter(f => f.status === 'pending').map((fb) => (
                    <div key={fb._id} className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row gap-4 items-center justify-between">
                      <div className="flex items-center gap-4 w-full md:w-auto">
                        {fb.analysisId?.fileUrl ? (
                          <img 
                            src={fb.analysisId.fileUrl} 
                            alt="Analysis" 
                            className="w-16 h-16 rounded-lg object-cover border border-slate-800"
                          />
                        ) : (
                          <div className="w-16 h-16 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-[10px] text-slate-500">No Image</div>
                        )}
                        <div>
                          <p className="text-xs font-bold text-slate-400">ID: {fb._id.slice(-6)}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">Submitted: {new Date(fb.createdAt).toLocaleDateString()}</p>
                          <div className="flex gap-2 mt-1.5">
                            <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-800/30">
                              System: {(fb.analysisId?.deepfakeProbability * 100).toFixed(0)}% Fake
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-400 border border-indigo-800/30">
                              User flagged as: {fb.userLabel.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex gap-2 w-full md:w-auto justify-end border-t border-slate-800 md:border-t-0 pt-3 md:pt-0">
                        <button
                          onClick={() => handleVerify(fb._id, 'verified', 'real')}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-400 rounded-lg text-xs font-bold border border-emerald-800/40 transition-colors"
                        >
                          <CheckCircle size={14} /> Verify Real
                        </button>
                        <button
                          onClick={() => handleVerify(fb._id, 'verified', 'fake')}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 rounded-lg text-xs font-bold border border-rose-800/40 transition-colors"
                        >
                          <ShieldX size={14} /> Verify Fake
                        </button>
                        <button
                          onClick={() => handleVerify(fb._id, 'rejected')}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg text-xs font-bold border border-slate-700 transition-colors"
                        >
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Model History Registry */}
            <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
              <h2 className="text-xl font-black mb-4 flex items-center gap-2">
                <History className="text-indigo-500" size={20} />
                Model Version Registry
              </h2>
              <div className="space-y-4 max-h-[450px] overflow-y-auto pr-2">
                {modelList.length === 0 ? (
                  <p className="text-slate-500 text-xs text-center py-8">No model versions registered in MongoDB database.</p>
                ) : (
                  modelList.map((model) => (
                    <div key={model._id} className={`p-4 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-4 transition-all ${
                      model.status === 'active' 
                        ? 'bg-indigo-950/20 border-indigo-500/40' 
                        : 'bg-slate-950/60 border-slate-800'
                    }`}>
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-black">{model.version}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded font-black tracking-wide uppercase ${
                            model.status === 'active' 
                              ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-400/30' 
                              : model.status === 'rolled_back'
                              ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}>
                            {model.status}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1">Created: {new Date(model.createdAt).toLocaleString()}</p>
                        <p className="text-[10px] text-indigo-400/80 mt-0.5">Trained samples: {model.trainedOnSamplesCount}</p>
                        
                        {/* Validation Metrics Grid */}
                        <div className="grid grid-cols-5 gap-2 mt-3 bg-slate-950/80 border border-slate-900 px-3 py-2 rounded-lg">
                          {Object.entries(model.metrics || {}).map(([key, val]) => (
                            <div key={key} className="text-center">
                              <p className="text-[8px] uppercase tracking-wider text-slate-500 font-bold">{key}</p>
                              <p className="text-xs font-black text-slate-300 mt-0.5">{(val * 100).toFixed(0)}%</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {model.status !== 'active' && (
                        <button
                          onClick={() => handleRollback(model.version)}
                          className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-bold border border-slate-800 transition-colors self-end md:self-center"
                        >
                          <RotateCcw size={14} /> Rollback to this Version
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* Right Column: Audit Logs & Statistics */}
          <div className="space-y-8">
            
            {/* System Audit Logs */}
            <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex flex-col h-full">
              <h2 className="text-xl font-black mb-4 flex items-center gap-2">
                <FileText className="text-indigo-500" size={20} />
                Audit Logs
              </h2>
              <div className="space-y-4 max-h-[800px] overflow-y-auto pr-2 flex-grow">
                {auditLogs.length === 0 ? (
                  <p className="text-slate-500 text-xs text-center py-8">No audit logs logged in system.</p>
                ) : (
                  auditLogs.map((log) => (
                    <div key={log._id} className="border-l-2 border-slate-800 pl-4 py-1 text-xs">
                      <p className="font-bold text-slate-300">
                        {log.action.replace(/_/g, ' ').toUpperCase()}
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        {new Date(log.createdAt).toLocaleString()}
                      </p>
                      {log.details && (
                        <pre className="mt-1.5 bg-slate-950 p-2 rounded text-[10px] text-slate-400 overflow-x-auto border border-slate-950">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};

export default AdminDashboard;
