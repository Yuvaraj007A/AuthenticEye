import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const FAQ = () => {
  const faqs = [
    { q: "What types of deepfakes can you detect?", a: "We can detect faceswaps, audio-driven lip syncing, full AI generated synthetic humans (GANs/Diffusion), and slight digital manipulations/retouches." },
    { q: "Is my uploaded media stored permanently?", a: "No. Unless you are authenticated on a paid Dashboard, API requests are processed entirely in-memory and discarded upon returning the inference." },
    { q: "How fast is the API?", a: "Our optimized PyTorch pipeline handles standard resolution imagery (1080p) in under 100 milliseconds." },
  ];

  const [openIdx, setOpenIdx] = useState(null);

  return (
    <div className="py-24 max-w-3xl mx-auto px-4">
      <h2 className="text-3xl font-bold mb-10 text-center">Frequently Asked <span className="text-emerald-600">Questions</span></h2>
      <div className="space-y-4">
        {faqs.map((faq, i) => (
          <div key={i} className="glass-card rounded-xl overflow-hidden cursor-pointer" onClick={() => setOpenIdx(openIdx === i ? null : i)}>
            <div className="p-5 flex justify-between items-center bg-slate-50 hover:bg-emerald-50 transition-colors">
              <h4 className="font-semibold text-lg text-gray-900">{faq.q}</h4>
              <ChevronDown className={`transform transition-transform ${openIdx === i ? 'rotate-180 text-emerald-600' : 'text-gray-400'}`} />
            </div>
            {openIdx === i && (
              <div className="p-5 text-slate-600 border-t border-slate-100 bg-white">
                {faq.a}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default FAQ;
