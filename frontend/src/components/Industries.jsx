import React from 'react';
import { motion } from 'framer-motion';
import { Building2, MessageSquareWarning, GraduationCap, Heart } from 'lucide-react';

const Industries = () => {
  const industries = [
    { title: "Banking KYC", icon: <Building2 className="w-8 h-8"/>, color: "text-emerald-400", bg: "bg-emerald-400/10" },
    { title: "Social Media Moderation", icon: <MessageSquareWarning className="w-8 h-8"/>, color: "text-rose-400", bg: "bg-rose-400/10" },
    { title: "Online Exam Proctoring", icon: <GraduationCap className="w-8 h-8"/>, color: "text-amber-400", bg: "bg-amber-400/10" },
    { title: "Dating Platforms", icon: <Heart className="w-8 h-8"/>, color: "text-pink-400", bg: "bg-pink-400/10" },
  ];

  return (
    <div className="py-24">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center mb-16 gap-8">
          <div className="max-w-xl">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Trusted Across <span className="text-gradient">Industries</span></h2>
            <p className="text-slate-600 text-lg">Identity verification is broken. We fix it for platforms where authenticity is critical to safety and compliance.</p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {industries.map((ind, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass-card p-6 rounded-2xl flex flex-col items-center text-center hover:bg-slate-50 transition-colors gap-4"
            >
              <div className={`p-4 rounded-full ${ind.bg} ${ind.color}`}>
                {ind.icon}
              </div>
              <h3 className="text-lg font-semibold">{ind.title}</h3>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Industries;
