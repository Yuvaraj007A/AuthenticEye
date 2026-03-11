const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const Analysis = require('../models/Analysis');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// ─── Multer Storage ─────────────────────────────────────────────────────────
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const dir = 'uploads/';
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        cb(null, dir);
    },
    filename: (req, file, cb) => {
        cb(null, `${Date.now()}${path.extname(file.originalname)}`);
    }
});

const uploadImage = multer({
    storage,
    limits: { fileSize: 15 * 1024 * 1024 }, // 15MB
    fileFilter: (req, file, cb) => {
        const ok = /jpeg|jpg|png|webp/.test(path.extname(file.originalname).toLowerCase())
            && /image\//.test(file.mimetype);
        ok ? cb(null, true) : cb(new Error('Images only (JPEG, PNG, WEBP)'));
    },
});

const uploadVideo = multer({
    storage,
    limits: { fileSize: 500 * 1024 * 1024 }, // 500MB
    fileFilter: (req, file, cb) => {
        const ok = /mp4|mov|avi|webm/.test(path.extname(file.originalname).toLowerCase());
        ok ? cb(null, true) : cb(new Error('Video only (MP4, MOV, AVI, WEBM)'));
    },
});

// ─── Helper: Optional JWT Auth ────────────────────────────────────────────────
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

// ─── Helper: Forward to AI ──────────────────────────────────────────────────
async function callAIService(endpoint, filePath, originalName, mimeType) {
    const formData = new FormData();
    formData.append('file', fs.createReadStream(filePath), {
        filename: originalName,
        contentType: mimeType,
    });
    const res = await axios.post(`${AI_SERVICE_URL}${endpoint}`, formData, {
        headers: formData.getHeaders(),
        timeout: 180000,
    });
    return res.data;
}

// ─── POST /api/detect/image ───────────────────────────────────────────────────
router.post('/image', uploadImage.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).json({ msg: 'No file uploaded' });
    const filePath = path.join(__dirname, '..', req.file.path);

    try {
        const ai = await callAIService('/detect/image', filePath, req.file.originalname, req.file.mimetype);

        const analysis = new Analysis({
            userId: extractUserId(req),
            fileUrl: `/uploads/${req.file.filename}`,
            mediaType: 'image',
            deepfakeProbability: ai.deepfake_probability,
            authenticityScore: ai.authenticity_score,
            ganProbability: ai.gan_probability ?? 0,
            diffusionProbability: ai.diffusion_probability ?? 0,
            heatmapBase64: ai.heatmap_base64 || '',
            modelScores: ai.model_scores || {},
            faceDetected: ai.face_detected ?? false,
        });

        await analysis.save();
        res.json({ ...analysis.toObject(), aiDetail: ai });

    } catch (err) {
        console.error('Image detection error:', err.message);
        res.status(500).json({ msg: 'AI service error', detail: err.message });
    } finally {
        try { fs.unlinkSync(filePath); } catch (_) {}
    }
});

// ─── POST /api/detect/video ───────────────────────────────────────────────────
router.post('/video', uploadVideo.single('video'), async (req, res) => {
    if (!req.file) return res.status(400).json({ msg: 'No file uploaded' });
    const filePath = path.join(__dirname, '..', req.file.path);

    try {
        const ai = await callAIService('/detect/video', filePath, req.file.originalname, req.file.mimetype);

        const analysis = new Analysis({
            userId: extractUserId(req),
            fileUrl: `/uploads/${req.file.filename}`,
            mediaType: 'video',
            deepfakeProbability: ai.deepfake_probability,
            authenticityScore: ai.authenticity_score,
            modelScores: ai.frame_score_stats || {},
        });

        await analysis.save();
        res.json({ ...analysis.toObject(), aiDetail: ai });

    } catch (err) {
        console.error('Video detection error:', err.message);
        res.status(500).json({ msg: 'AI service error', detail: err.message });
    } finally {
        try { fs.unlinkSync(filePath); } catch (_) {}
    }
});

module.exports = router;
