const express = require('express');
const router = express.Router();
const Feedback = require('../models/Feedback');
const Analysis = require('../models/Analysis');
const AuditLog = require('../models/AuditLog');
const jwt = require('jsonwebtoken');

function extractUserId(req) {
    try {
        const authHeader = req.header('Authorization');
        if (authHeader) {
            const token = authHeader.split(' ')[1];
            const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret_key');
            return decoded.user.id;
        }
    } catch (_) {}
    return null;
}

// POST /api/feedback - Submit new feedback correction
router.post('/', async (req, res) => {
    const { analysisId, userLabel } = req.body;
    if (!analysisId || !userLabel) {
        return res.status(400).json({ msg: 'Missing analysisId or userLabel' });
    }

    try {
        const analysis = await Analysis.findById(analysisId);
        if (!analysis) {
            return res.status(404).json({ msg: 'Analysis record not found' });
        }

        const userId = extractUserId(req);
        const systemProb = analysis.deepfakeProbability;
        const prediction = systemProb > 0.5 ? 'fake' : 'real';
        const confidence = prediction === 'fake' ? systemProb : (1.0 - systemProb);

        // Create feedback entry using new and legacy properties
        const feedback = new Feedback({
            userId,
            imageId: analysisId,
            prediction,
            actualLabel: userLabel,
            confidence,
            reviewed: false,
            timestamp: new Date(),

            // Legacy compatibility
            analysisId,
            userLabel,
            status: 'pending'
        });

        await feedback.save();

        // Audit Log
        const audit = new AuditLog({
            action: 'user_feedback_submitted',
            userId: userId,
            details: {
                feedbackId: feedback._id,
                analysisId,
                userLabel,
                prediction,
                confidence
            }
        });
        await audit.save();

        res.json({ msg: 'Feedback submitted successfully', feedback });
    } catch (err) {
        console.error('Feedback submission error:', err.message);
        res.status(500).json({ msg: 'Database error', detail: err.message });
    }
});

module.exports = router;
