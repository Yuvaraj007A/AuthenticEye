const mongoose = require('mongoose');

const AnalysisSchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        default: null,
    },
    fileUrl: { type: String },
    mediaType: { type: String, enum: ['image', 'video'], default: 'image' },
    deepfakeProbability: { type: Number, required: true },
    authenticityScore: { type: Number, required: true },
    ganProbability: { type: Number, default: 0 },
    diffusionProbability: { type: Number, default: 0 },
    heatmapBase64: { type: String, default: '' },
    modelScores: { type: Object, default: {} },
    faceDetected: { type: Boolean, default: false },
    
    // Upgraded Phase 15 schema fields
    prediction: { type: String, enum: ['AI_GENERATED', 'REAL'] },
    confidence: { type: Number },
    riskLevel: { type: String, enum: ['HIGH', 'MEDIUM', 'LOW'] },
    scores: { type: Object, default: {} },
    explanation: { type: Object, default: {} },
    evidence: { type: Object, default: {} },
    
    // Upgraded Phase 5 & 6 schema fields
    image: { type: String }, // URL of original image
    result: { type: String, enum: ['real', 'fake'] },
    modelVersion: { type: String, default: 'v1' },
    explanationAssets: {
        gradcamUrl: { type: String, default: '' },
        fftUrl: { type: String, default: '' },
        ganUrl: { type: String, default: '' },
        faceboxUrl: { type: String, default: '' }
    },
    
    createdAt: { type: Date, default: Date.now },
});

module.exports = mongoose.model('Analysis', AnalysisSchema);
