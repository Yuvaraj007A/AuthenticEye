const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const mongoose = require('mongoose');
const Feedback = require('../models/Feedback');
const Analysis = require('../models/Analysis');
const ModelVersion = require('../models/ModelVersion');
const AuditLog = require('../models/AuditLog');
const User = require('../models/User');
const auth = require('../middleware/authMiddleware');
const adminAuth = require('../middleware/adminMiddleware');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// Helper: Extract userId if present
function extractUserId(req) {
    try {
        if (req.header('Authorization')) {
            const jwt = require('jsonwebtoken');
            const token = req.header('Authorization').split(' ')[1];
            const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret_key');
            return decoded.user.id;
        }
    } catch (_) {}
    return null;
}

// GET /api/admin/feedback - List all feedback
router.get('/feedback', [auth, adminAuth], async (req, res) => {
    try {
        const list = await Feedback.find().populate('analysisId').sort({ createdAt: -1 });
        res.json(list);
    } catch (err) {
        res.status(500).json({ msg: 'Database error', detail: err.message });
    }
});

// POST /api/admin/feedback/verify - Verify or reject a feedback
router.post('/feedback/verify', [auth, adminAuth], async (req, res) => {
    const { feedbackId, status, verifiedLabel } = req.body;
    if (!feedbackId || !status) {
        return res.status(400).json({ msg: 'Missing feedbackId or status' });
    }

    try {
        const feedback = await Feedback.findById(feedbackId).populate('analysisId');
        if (!feedback) {
            return res.status(404).json({ msg: 'Feedback record not found' });
        }

        feedback.status = status;
        feedback.reviewed = true;
        feedback.reviewer = req.user.id;
        feedback.timestamp = new Date();

        if (status === 'verified') {
            feedback.verifiedLabel = verifiedLabel || feedback.userLabel || feedback.actualLabel;

            const analysis = feedback.analysisId || feedback.imageId;
            if (analysis && analysis.fileUrl) {
                const srcPath = path.join(__dirname, '..', 'uploads', path.basename(analysis.fileUrl));
                if (fs.existsSync(srcPath)) {
                    const category = feedback.verifiedLabel === 'real' ? 'real' : 'fake';

                    // 1. Copy to ai-service training/verified_data
                    const destDirAI = path.join(__dirname, '..', '..', 'ai-service', 'training', 'verified_data', category);
                    fs.mkdirSync(destDirAI, { recursive: true });
                    const destPathAI = path.join(destDirAI, path.basename(analysis.fileUrl));
                    fs.copyFileSync(srcPath, destPathAI);
                    console.log(`Copied verified file to AI service: ${destPathAI}`);

                    // 2. Copy to workspace root feedback_dataset/verified_dataset
                    const destDirRoot = path.join(__dirname, '..', '..', 'feedback_dataset', 'verified_dataset', category);
                    fs.mkdirSync(destDirRoot, { recursive: true });
                    const destPathRoot = path.join(destDirRoot, path.basename(analysis.fileUrl));
                    fs.copyFileSync(srcPath, destPathRoot);
                    console.log(`Copied verified file to root dataset: ${destPathRoot}`);
                } else {
                    console.warn(`Source file not found at: ${srcPath}`);
                }
            }
        }

        await feedback.save();

        // Audit Log
        const audit = new AuditLog({
            action: `feedback_${status}`,
            userId: req.user.id,
            details: {
                feedbackId,
                status,
                verifiedLabel: feedback.verifiedLabel
            }
        });
        await audit.save();

        res.json({ msg: `Feedback successfully ${status}`, feedback });

    } catch (err) {
        console.error('Feedback verification error:', err.message);
        res.status(500).json({ msg: 'Database error', detail: err.message });
    }
});

// POST /api/admin/retrain - Trigger model retraining in AI Service
router.post('/retrain', [auth, adminAuth], async (req, res) => {
    try {
        const adminId = req.user.id;

        // Call FastAPI retraining endpoint
        const response = await axios.post(`${AI_SERVICE_URL}/retrain`, {
            trigger: 'admin'
        }, { timeout: 600000 }); // 10 min timeout for CPU training

        const { version, metrics, efficientnetPath, xceptionnetPath, vitPath, trained_samples } = response.data;

        // Set previous active models to inactive
        await ModelVersion.updateMany({ status: 'active' }, { status: 'inactive' });

        // Save new active ModelVersion
        const newVersion = new ModelVersion({
            version,
            status: 'active',
            metrics,
            efficientnetPath,
            xceptionnetPath,
            vitPath,
            trainedOnSamplesCount: trained_samples
        });
        await newVersion.save();

        // Mark all verified feedback as used in retraining
        await Feedback.updateMany({ status: 'verified', isUsedInRetraining: false }, { isUsedInRetraining: true });

        // Audit Log
        const audit = new AuditLog({
            action: 'retraining_completed',
            userId: adminId,
            details: {
                version,
                metrics,
                trainedOnSamplesCount: trained_samples
            }
        });
        await audit.save();

        res.json({ msg: 'Retraining completed successfully', modelVersion: newVersion });

    } catch (err) {
        console.error('Retraining trigger error:', err.message);
        res.status(500).json({ msg: 'Retraining failed', detail: err.message });
    }
});

// GET /api/admin/models - Get list of all model versions
router.get('/models', [auth, adminAuth], async (req, res) => {
    try {
        const list = await ModelVersion.find().sort({ createdAt: -1 });
        res.json(list);
    } catch (err) {
        res.status(500).json({ msg: 'Database error', detail: err.message });
    }
});

// POST /api/admin/models/rollback - Rollback active model to a previous version
router.post('/models/rollback', [auth, adminAuth], async (req, res) => {
    const { version } = req.body;
    if (!version) {
        return res.status(400).json({ msg: 'Missing version parameter' });
    }

    try {
        const adminId = req.user.id;
        const targetVersion = await ModelVersion.findOne({ version });
        if (!targetVersion) {
            return res.status(404).json({ msg: 'Model version not found' });
        }

        // Call FastAPI rollback endpoint to load target checkpoints
        await axios.post(`${AI_SERVICE_URL}/rollback`, {
            version,
            efficientnetPath: targetVersion.efficientnetPath,
            xceptionnetPath: targetVersion.xceptionnetPath,
            vitPath: targetVersion.vitPath
        });

        // Update database statuses
        await ModelVersion.updateMany({ status: 'active' }, { status: 'inactive' });
        targetVersion.status = 'active';
        await targetVersion.save();

        // Audit Log
        const audit = new AuditLog({
            action: 'model_rolled_back',
            userId: adminId,
            details: {
                version
            }
        });
        await audit.save();

        res.json({ msg: `Successfully rolled back to version ${version}`, modelVersion: targetVersion });

    } catch (err) {
        console.error('Rollback error:', err.message);
        res.status(500).json({ msg: 'Rollback failed', detail: err.message });
    }
});

// GET /api/admin/audit-logs - Fetch audit logs
router.get('/audit-logs', [auth, adminAuth], async (req, res) => {
    try {
        const logs = await AuditLog.find().populate('userId').sort({ createdAt: -1 }).limit(100);
        res.json(logs);
    } catch (err) {
        res.status(500).json({ msg: 'Database error', detail: err.message });
    }
});

// GET /api/admin/analytics - System, User, and AI analytics
router.get('/analytics', [auth, adminAuth], async (req, res) => {
    try {
        // 1. User stats
        const totalUsers = await User.countDocuments();
        const activeUsersCount = await Analysis.distinct('userId');
        const activeUsers = activeUsersCount.filter(id => id !== null).length;

        // 2. AI stats
        const totalDetections = await Analysis.countDocuments();
        const imagesCount = await Analysis.countDocuments({ mediaType: 'image' });
        const videosCount = await Analysis.countDocuments({ mediaType: 'video' });
        
        const fakesCount = await Analysis.countDocuments({ result: 'fake' });
        const realsCount = await Analysis.countDocuments({ result: 'real' });

        // Calculate average confidence
        const avgConfidenceAgg = await Analysis.aggregate([
            { $group: { _id: null, avgConfidence: { $avg: '$confidence' } } }
        ]);
        const avgConfidence = avgConfidenceAgg[0] ? avgConfidenceAgg[0].avgConfidence : 0;

        // 3. System health
        const dbState = mongoose.connection.readyState;
        const dbStatus = dbState === 1 ? 'healthy' : 'unhealthy';


        // 4. Live performance metrics from the active model version
        const activeModel = await ModelVersion.findOne({ status: 'active' });

        res.json({
            users: {
                totalUsers,
                activeUsers,
            },
            ai: {
                totalDetections,
                imagesCount,
                videosCount,
                fakesCount,
                realsCount,
                avgConfidence: avgConfidence ? parseFloat(avgConfidence.toFixed(4)) : 0,
                activeModelVersion: activeModel ? activeModel.version : 'v1',
                activeModelMetrics: activeModel ? activeModel.metrics : null
            },
            system: {
                database: dbStatus,
                mongooseState: dbState,
            }
        });
    } catch (err) {
        console.error('Analytics error:', err.message);
        res.status(500).json({ msg: 'Failed to compile analytics', detail: err.message });
    }
});

module.exports = router;
