const mongoose = require('mongoose');

const ModelVersionSchema = new mongoose.Schema({
    version: {
        type: String,
        required: true,
        unique: true,
    },
    status: {
        type: String,
        enum: ['active', 'rolled_back', 'inactive'],
        default: 'inactive',
    },
    metrics: {
        type: Object,
        default: {
            accuracy: 0,
            precision: 0,
            recall: 0,
            f1: 0,
            auc: 0,
        },
    },
    efficientnetPath: { type: String, default: '' },
    xceptionnetPath: { type: String, default: '' },
    vitPath: { type: String, default: '' },
    trainedOnSamplesCount: { type: Number, default: 0 },
    createdAt: {
        type: Date,
        default: Date.now,
    },
});

module.exports = mongoose.model('ModelVersion', ModelVersionSchema);
