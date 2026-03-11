import React from 'react';
import { motion } from 'framer-motion';

const Metrics = () => {
  return (
    <div className="py-20 bg-emerald-50/30 border-y border-emerald-100/50 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 relative z-10">
        <div className="grid md:grid-cols-3 gap-8 text-center divide-y md:divide-y-0 md:divide-x divide-slate-200">
          
          <motion.div 
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            className="py-6"
          >
            <div className="text-5xl font-extrabold text-slate-900 mb-2">92%</div>
            <div className="text-emerald-600 font-medium uppercase tracking-wider text-sm">Accuracy Rate</div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: 0.2 }}
            className="py-6"
          >
            <div className="text-5xl font-extrabold text-slate-900 mb-2">&lt;100ms</div>
            <div className="text-violet-600 font-medium uppercase tracking-wider text-sm">Detection Speed</div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: 0.4 }}
            className="py-6"
          >
            <div className="text-5xl font-extrabold text-slate-900 mb-2">94%</div>
            <div className="text-rose-600 font-medium uppercase tracking-wider text-sm">Synthetic Detection Scope</div>
          </motion.div>

        </div>
      </div>
    </div>
  );
};

export default Metrics;
