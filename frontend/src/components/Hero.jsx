import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowRight } from 'lucide-react';

const Hero = () => {
  return (
    <div className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute top-0 left-1/4 -translate-x-1/2 w-[600px] h-[600px] bg-emerald-500/5 rounded-full blur-[120px] z-0 pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 translate-x-1/2 w-[500px] h-[500px] bg-violet-500/5 rounded-full blur-[100px] z-0 pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-4 relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card text-emerald-600 text-sm font-semibold mb-6">
            <ShieldCheck size={18} /> Deepfake Detection Engine v2.0 Live
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
            Humans Guess. <br className="hidden md:block"/>
            <span className="text-gradient">AI Knows.</span>
          </h1>
          
          <p className="max-w-2xl mx-auto text-lg md:text-xl text-slate-600 mb-10">
            Secure your platform against manipulated media. Our military-grade detection system identifies AI-generated faces, deepfakes, and synthesized content in milliseconds.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <Link to="/demo" className="w-full sm:w-auto px-8 py-3 rounded-lg bg-primary hover:bg-emerald-700 text-white font-semibold transition-all flex items-center justify-center gap-2 transform hover:scale-105">
              Try Demo <ArrowRight size={18} />
            </Link>
            <Link to="/register" className="w-full sm:w-auto px-8 py-3 rounded-lg border border-slate-200 hover:border-primary text-slate-700 font-semibold transition-all glass-card">
              Book Demo
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Hero;
