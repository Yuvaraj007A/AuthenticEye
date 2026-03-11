import React from 'react';
import { motion } from 'framer-motion';
import { ScanFace, ImagePlus, Fingerprint } from 'lucide-react';

const Features = () => {
  const features = [
    {
      icon: <ScanFace className="w-10 h-10 text-emerald-500 mb-4" />,
      title: "Faceswap Detection",
      desc: "Analyzes blending boundaries, mismatched facial features, and temporal inconsistencies in videos to detect face swapping."
    },
    {
      icon: <ImagePlus className="w-10 h-10 text-violet-500 mb-4" />,
      title: "AI Generated Image Detection",
      desc: "Identifies traces of GANs and Diffusion models (Midjourney, DALL-E) by analyzing pixel level noise patterns."
    },
    {
      icon: <Fingerprint className="w-10 h-10 text-rose-500 mb-4" />,
      title: "Manipulation Detection",
      desc: "Detects localized image tampering like cloning, splicing, and digital retouching on official documents."
    }
  ];

  return (
    <div className="py-24 bg-emerald-50/20">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Unrivaled <span className="text-gradient">Detection Capabilities</span></h2>
          <p className="text-slate-600 max-w-2xl mx-auto">Our multi-modal engine catches what the human eye misses.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.2 }}
              className="glass-card p-8 rounded-2xl hover:-translate-y-2 transition-transform duration-300 pointer-events-auto"
            >
              {f.icon}
              <h3 className="text-xl font-semibold mb-3">{f.title}</h3>
              <p className="text-slate-600 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Features;
