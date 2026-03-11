import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import api from '../services/api';

const UploadAnalyzer = ({ onResult }) => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    setError('');
    const selected = e.target.files[0];
    if (selected) {
      if (!selected.type.startsWith('image/')) {
        setError('Please upload an image file (JPEG, PNG, WEBP).');
        return;
      }
      if (selected.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10MB limit.');
        return;
      }
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
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

  const scanImage = async () => {
    if (!file) return;
    setIsUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await api.post('/detect', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      onResult(res.data, preview);
      setFile(null);
      setPreview(null);
    } catch (err) {
      console.error(err);
      setError('Analysis failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full">
      <div 
        className="glass-card border-2 border-dashed border-slate-200 rounded-2xl p-8 text-center transition-all hover:border-emerald-400 hover:bg-emerald-50/50"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {!preview ? (
          <div className="flex flex-col items-center justify-center py-10 cursor-pointer" onClick={() => fileInputRef.current.click()}>
            <UploadCloud className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-xl font-medium mb-2">Drag & Drop your image</h3>
            <p className="text-gray-500 mb-6">or click to browse from your device</p>
            <div className="bg-slate-100 px-4 py-2 rounded-lg text-sm text-slate-600">Supports JPG, PNG, WEBP (Max 10MB)</div>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <img src={preview} alt="Preview" className="max-h-64 object-contain rounded-lg mb-6 shadow-lg shadow-black/50" />
            <div className="flex gap-4 w-full justify-center">
              <button 
                onClick={() => { setFile(null); setPreview(null); }}
                className="px-6 py-2 rounded-lg border border-gray-600 hover:bg-white/10 transition"
              >
                Cancel
              </button>
              <button 
                onClick={scanImage} 
                disabled={isUploading}
                className="px-6 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium flex items-center gap-2 transition disabled:opacity-50"
              >
                {isUploading ? <><Loader2 className="animate-spin" size={18}/> Analyzing...</> : <><CheckCircle size={18}/> Start Analysis</>}
              </button>
            </div>
          </div>
        )}
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden" 
          accept="image/*"
          onChange={handleFileChange}
        />
      </div>
      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-3 text-red-400">
           <AlertCircle size={20} /> {error}
        </div>
      )}
    </div>
  );
};

export default UploadAnalyzer;
