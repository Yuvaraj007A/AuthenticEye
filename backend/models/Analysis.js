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
    createdAt: { type: Date, default: Date.now },
});

module.exports = mongoose.model('Analysis', AnalysisSchema);
