const mongoose = require('mongoose');

const FeedbackSchema = new mongoose.Schema({
    userId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        default: null,
    },
    imageId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Analysis',
        required: true,
    },
    prediction: {
        type: String,
        enum: ['real', 'fake'],
        required: true,
    },
    actualLabel: {
        type: String,
        enum: ['real', 'fake'],
        required: true,
    },
    confidence: {
        type: Number,
        default: 0.0,
    },
    reviewed: {
        type: Boolean,
        default: false,
    },
    reviewer: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        default: null,
    },
    timestamp: {
        type: Date,
        default: Date.now,
    },
    // Keep legacy fields for backward compatibility
    analysisId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Analysis',
    },
    userLabel: {
        type: String,
        enum: ['real', 'fake'],
    },
    status: {
        type: String,
        enum: ['pending', 'verified', 'rejected'],
        default: 'pending',
    },
    verifiedLabel: {
        type: String,
        enum: ['real', 'fake'],
        default: null,
    },
    isUsedInRetraining: {
        type: Boolean,
        default: false,
    },
    createdAt: {
        type: Date,
        default: Date.now,
    },
});

module.exports = mongoose.model('Feedback', FeedbackSchema);
