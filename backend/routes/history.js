const express = require('express');
const router = express.Router();
const Analysis = require('../models/Analysis');
const auth = require('../middleware/authMiddleware');

// GET /api/history — Get user's analysis history (authenticated)
router.get('/', auth, async (req, res) => {
    try {
        const history = await Analysis.find({ userId: req.user.id })
            .sort({ createdAt: -1 })
            .limit(50);
        res.json(history);
    } catch (err) {
        console.error(err.message);
        res.status(500).json({ msg: 'Server error fetching history' });
    }
});

// GET /api/history/:id — Single analysis record
router.get('/:id', auth, async (req, res) => {
    try {
        const record = await Analysis.findOne({ _id: req.params.id, userId: req.user.id });
        if (!record) return res.status(404).json({ msg: 'Analysis not found' });
        res.json(record);
    } catch (err) {
        res.status(500).json({ msg: 'Server error' });
    }
});

// DELETE /api/history/:id — Delete analysis record
router.delete('/:id', auth, async (req, res) => {
    try {
        const record = await Analysis.findOneAndDelete({ _id: req.params.id, userId: req.user.id });
        if (!record) return res.status(404).json({ msg: 'Analysis not found' });
        res.json({ msg: 'Deleted' });
    } catch (err) {
        res.status(500).json({ msg: 'Server error' });
    }
});

module.exports = router;
