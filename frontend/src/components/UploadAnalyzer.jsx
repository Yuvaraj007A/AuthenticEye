import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, Loader2, Image as ImageIcon, Trash2, FileText } from 'lucide-react';
import api from '../services/api';

const UploadAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    setError('');
    setResult(null);
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    const selectedFile = files[0];
    if (!/\.(jpeg|jpg|png|webp)$/i.test(selectedFile.name)) {
      setError('Only image files (JPEG, PNG, WEBP) are supported.');
      return;
    }
    
    if (selectedFile.size > 15 * 1024 * 1024) {
      setError('Image file exceeds the 15MB size limit.');
      return;
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange({ target: { files: e.dataTransfer.files } });
    }
  };

  const removeFile = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError('');
    setProgress(0);
  };

  const startAnalysis = async () => {
    if (!file) return;
    setIsUploading(true);
    setError('');
    setProgress(10);

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await api.post('/detect/image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (e) => {
          const up = Math.min(Math.round((e.loaded / e.total) * 90), 90);
          setProgress(up);
        }
      });

      setProgress(100);
      setResult(res.data);
      setIsUploading(false);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.msg || err.response?.data?.detail || 'Forensic analysis failed.');
      setIsUploading(false);
    }
  };

  const downloadReport = async (analysisId) => {
    try {
      const response = await api.get(`/history/${analysisId}/report`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Forensic-Report-${analysisId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Forensic report download error:', err);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto space-y-6">
      {!file && !result ? (
        <div 
          className="glass-card border-2 border-dashed border-slate-200 rounded-2xl p-8 text-center transition-all hover:border-emerald-400 hover:bg-emerald-50/50 cursor-pointer"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
        >
          <div className="flex flex-col items-center justify-center py-10">
            <UploadCloud className="w-16 h-16 text-emerald-500 mb-4" />
            <h3 className="text-xl font-bold text-gray-900 mb-2">Drag & Drop Image</h3>
            <p className="text-gray-500 text-sm mb-6">or click to browse from your device</p>
            <div className="flex flex-wrap justify-center gap-2">
              <span className="bg-slate-100 px-3 py-1 rounded-full text-xs text-slate-600 font-medium">JPEG, PNG, WEBP (Max 15MB)</span>
            </div>
          </div>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept="image/*"
            onChange={handleFileChange}
          />
        </div>
      ) : null}

      {file && !result && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="font-bold text-gray-900 text-sm flex items-center gap-2">
              <ImageIcon size={16} className="text-emerald-500" />
              Selected File
            </h4>
            <button 
              onClick={removeFile}
              className="text-xs text-rose-500 font-bold hover:underline"
            >
              Cancel
            </button>
          </div>

          <div className="flex flex-col items-center gap-4">
            {preview && (
              <img 
                src={preview} 
                alt="Upload preview" 
                className="max-h-48 rounded-lg shadow-sm border border-slate-100 object-contain"
              />
            )}
            <div className="flex items-center gap-2 text-xs text-slate-700">
              <span className="font-semibold truncate max-w-[250px]">{file.name}</span>
              <span className="text-slate-400">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
            </div>
          </div>

          {isUploading && (
            <div className="space-y-2 pt-2">
              <div className="flex justify-between text-xs text-slate-500">
                <span>Analyzing image authenticity...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-indigo-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {!isUploading && (
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={removeFile}
                className="px-4 py-2 border border-slate-200 text-slate-600 font-bold text-xs rounded-xl hover:bg-slate-50 transition"
              >
                Clear
              </button>
              <button
                onClick={startAnalysis}
                className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl flex items-center gap-2 transition shadow-sm"
              >
                Start Forensic Analysis
              </button>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="bg-white border border-emerald-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="font-bold text-gray-900 text-sm flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-500" />
              Analysis Completed
            </h4>
            <button 
              onClick={removeFile}
              className="text-xs text-emerald-600 font-bold hover:underline"
            >
              Analyze Another Image
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 py-2">
            <div className="p-4 bg-slate-50 rounded-xl text-center">
              <span className="text-xs text-slate-500 font-medium">Verdict</span>
              <p className={`text-lg font-black uppercase mt-1 ${result.result === 'fake' ? 'text-rose-600' : 'text-emerald-600'}`}>
                {result.result}
              </p>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl text-center">
              <span className="text-xs text-slate-500 font-medium">Confidence</span>
              <p className="text-lg font-black text-slate-800 mt-1">
                {(result.confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <span className="text-xs text-slate-400">Model: {result.modelVersion || 'v1'}</span>
            <button 
              onClick={() => downloadReport(result._id)}
              className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-lg font-bold text-xs flex items-center gap-1.5 transition"
            >
              <FileText size={12} /> Download PDF Report
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-700 text-xs font-semibold">
           <AlertCircle size={18} /> {error}
        </div>
      )}
    </div>
  );
};

export default UploadAnalyzer;
