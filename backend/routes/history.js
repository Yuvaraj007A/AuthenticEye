const express = require('express');
const router = express.Router();
const Analysis = require('../models/Analysis');
const auth = require('../middleware/authMiddleware');

// GET /api/history — Get user's analysis history with search, filter, sort, and pagination (authenticated)
router.get('/', auth, async (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 10;
        const search = req.query.search || '';
        const filter = req.query.filter || 'all'; // 'all', 'real', 'fake'
        const sort = req.query.sort || 'newest'; // 'newest', 'oldest', 'confidence_high', 'confidence_low'

        // Build query
        const query = { userId: req.user.id };

        // Search by mediaType or filename pattern
        if (search) {
            query.$or = [
                { mediaType: { $regex: search, $options: 'i' } },
                { fileUrl: { $regex: search, $options: 'i' } }
            ];
        }

        // Filter by result / probability
        if (filter === 'real') {
            query.deepfakeProbability = { $lte: 0.5 };
        } else if (filter === 'fake') {
            query.deepfakeProbability = { $gt: 0.5 };
        }

        // Sort option
        let sortOption = { createdAt: -1 };
        if (sort === 'oldest') {
            sortOption = { createdAt: 1 };
        } else if (sort === 'confidence_high') {
            sortOption = { deepfakeProbability: -1 };
        } else if (sort === 'confidence_low') {
            sortOption = { deepfakeProbability: 1 };
        }

        // Pagination
        const total = await Analysis.countDocuments(query);
        const history = await Analysis.find(query)
            .sort(sortOption)
            .skip((page - 1) * limit)
            .limit(limit);

        res.json({
            total,
            page,
            pages: Math.ceil(total / limit),
            data: history
        });
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

const { generateForensicPDF } = require('../scripts/pdfGenerator');

// GET /api/history/:id/report — Generate and download PDF Forensic Report
router.get('/:id/report', auth, async (req, res) => {
    try {
        const record = await Analysis.findOne({ _id: req.params.id, userId: req.user.id });
        if (!record) return res.status(404).json({ msg: 'Analysis not found' });

        const pdfBuffer = await generateForensicPDF(record);

        res.setHeader('Content-Type', 'application/pdf');
        res.setHeader('Content-Disposition', `attachment; filename=AuthenticEye_Report_${req.params.id}.pdf`);
        res.send(pdfBuffer);
    } catch (err) {
        console.error('PDF generation error:', err);
        res.status(500).json({ msg: 'Failed to generate PDF report', detail: err.message });
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
