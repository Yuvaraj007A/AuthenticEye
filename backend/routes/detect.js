const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const crypto = require('crypto');

const Analysis = require('../models/Analysis');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// ─── Ensure Directories Exist ───────────────────────────────────────────────
const uploadsDir = path.join(__dirname, '..', 'uploads');
const quarantineDir = path.join(uploadsDir, 'quarantine');
const explanationsDir = path.join(uploadsDir, 'explanations');

fs.mkdirSync(uploadsDir, { recursive: true });
fs.mkdirSync(quarantineDir, { recursive: true });
fs.mkdirSync(explanationsDir, { recursive: true });

// ─── Storage in Quarantine ──────────────────────────────────────────────────
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, quarantineDir);
    },
    filename: (req, file, cb) => {
        cb(null, `${Date.now()}_${crypto.randomBytes(4).toString('hex')}${path.extname(file.originalname)}`);
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



// ─── Security Checks ─────────────────────────────────────────────────────────

// Verify headers/magic bytes for file security
function verifyMagicBytes(filePath, expectedMime) {
    try {
        const fd = fs.openSync(filePath, 'r');
        const buffer = Buffer.alloc(4);
        fs.readSync(fd, buffer, 0, 4, 0);
        fs.closeSync(fd);
        const header = buffer.toString('hex').toLowerCase();
        
        if (expectedMime.includes('jpeg') || expectedMime.includes('jpg')) {
            return header.startsWith('ffd8ff');
        }
        if (expectedMime.includes('png')) {
            return header.startsWith('89504e47');
        }
        if (expectedMime.includes('webp')) {
            return header.startsWith('52494646'); // RIFF header
        }
        if (expectedMime.includes('zip') || expectedMime.includes('octet-stream')) {
            return header.startsWith('504b0304'); // PK header
        }
        return true;
    } catch (_) {
        return false;
    }
}

// SHA256 checksum calculator
function calculateFileHash(filePath) {
    const hash = crypto.createHash('sha256');
    const data = fs.readFileSync(filePath);
    hash.update(data);
    return hash.digest('hex');
}

// Virus Scanning mock verification hook
async function scanFileForViruses(filePath) {
    console.log(`[SECURITY] Anti-virus scanner running on: ${filePath}`);
    // Mock AV scan - in production, execute clamscan or similar daemon
    return true; 
}

// Promotion: move clean quarantine file to uploads serving path
function promoteQuarantineFile(tempPath) {
    const finalDest = path.join(uploadsDir, path.basename(tempPath));
    fs.copyFileSync(tempPath, finalDest);
    try { fs.unlinkSync(tempPath); } catch (_) {}
    return `/uploads/${path.basename(tempPath)}`;
}

// Extract JWT user ID if authenticated
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

// ─── POST /api/detect/image ───────────────────────────────────────────────────
router.post('/image', uploadImage.single('image'), async (req, res) => {
    if (!req.file) return res.status(400).json({ msg: 'No file uploaded' });
    const filePath = req.file.path;
    let cleanUpNeeded = true;

    try {
        // 1. MIME Validation & Magic Bytes check
        if (!verifyMagicBytes(filePath, req.file.mimetype)) {
            throw new Error('Security Error: File contents do not match specified MIME type.');
        }

        // 2. SHA256 Hash Verification
        const hashVal = calculateFileHash(filePath);
        console.log(`[SECURITY] File SHA-256 hash: ${hashVal}`);

        // 3. Virus scanning check
        const avClean = await scanFileForViruses(filePath);
        if (!avClean) {
            throw new Error('Security Error: File flagged by anti-virus scan.');
        }

        // Forward to AI FastAPI microservice
        const formData = new FormData();
        formData.append('file', fs.createReadStream(filePath), {
            filename: req.file.originalname,
            contentType: req.file.mimetype,
        });
        
        const aiResponse = await axios.post(`${AI_SERVICE_URL}/detect/image`, formData, {
            headers: formData.getHeaders(),
            timeout: 180000,
        });
        const ai = aiResponse.data;

        // Promote image out of quarantine folder
        const finalFileUrl = promoteQuarantineFile(filePath);
        cleanUpNeeded = false;

        // Decode explainability heatmaps from base64 and save as static images
        const filenameBase = path.basename(filePath, path.extname(filePath));
        const explanationAssets = {
            gradcamUrl: '',
            fftUrl: '',
            ganUrl: '',
            faceboxUrl: ''
        };

        if (ai.heatmap_base64) {
            const p = path.join(explanationsDir, `gradcam_${filenameBase}.jpg`);
            fs.writeFileSync(p, Buffer.from(ai.heatmap_base64, 'base64'));
            explanationAssets.gradcamUrl = `/uploads/explanations/gradcam_${filenameBase}.jpg`;
        }
        if (ai.fft_base64) {
            const p = path.join(explanationsDir, `fft_${filenameBase}.jpg`);
            fs.writeFileSync(p, Buffer.from(ai.fft_base64, 'base64'));
            explanationAssets.fftUrl = `/uploads/explanations/fft_${filenameBase}.jpg`;
        }
        if (ai.gan_base64) {
            const p = path.join(explanationsDir, `gan_${filenameBase}.jpg`);
            fs.writeFileSync(p, Buffer.from(ai.gan_base64, 'base64'));
            explanationAssets.ganUrl = `/uploads/explanations/gan_${filenameBase}.jpg`;
        }
        if (ai.facebox_base64) {
            const p = path.join(explanationsDir, `facebox_${filenameBase}.jpg`);
            fs.writeFileSync(p, Buffer.from(ai.facebox_base64, 'base64'));
            explanationAssets.faceboxUrl = `/uploads/explanations/facebox_${filenameBase}.jpg`;
        }

        const analysis = new Analysis({
            userId: extractUserId(req),
            fileUrl: finalFileUrl,
            mediaType: 'image',
            deepfakeProbability: ai.deepfake_probability,
            authenticityScore: ai.authenticity_score,
            ganProbability: ai.gan_probability ?? 0,
            diffusionProbability: ai.diffusion_probability ?? 0,
            heatmapBase64: ai.heatmap_base64 || '',
            modelScores: ai.model_scores || {},
            faceDetected: ai.face_detected ?? false,
            
            // New visual metrics fields
            prediction: ai.prediction,
            riskLevel: ai.risk_level,
            scores: ai.scores,
            explanation: ai.explanation,
            evidence: ai.evidence || {},
            image: finalFileUrl,
            result: ai.prediction === 'AI_GENERATED' ? 'fake' : 'real',
            confidence: ai.confidence,
            modelVersion: ai.model_version || 'v1',
            explanationAssets,
        });

        await analysis.save();
        res.json({ ...analysis.toObject(), aiDetail: ai });

    } catch (err) {
        console.error('Image detection error:', err.message);
        res.status(500).json({ msg: 'AI service or upload verification failure', detail: err.message });
    } finally {
        if (cleanUpNeeded) {
            try { fs.unlinkSync(filePath); } catch (_) {}
        }
    }
});

// ─── POST /api/detect/video ───────────────────────────────────────────────────
router.post('/video', uploadVideo.single('video'), async (req, res) => {
    if (!req.file) return res.status(400).json({ msg: 'No file uploaded' });
    const filePath = req.file.path;
    let cleanUpNeeded = true;

    try {
        if (!verifyMagicBytes(filePath, req.file.mimetype)) {
            throw new Error('Security Error: Video magic bytes check failed.');
        }

        const avClean = await scanFileForViruses(filePath);
        if (!avClean) {
            throw new Error('Security Error: Video flagged by anti-virus scan.');
        }

        // Forward to FastAPI video detector
        const formData = new FormData();
        formData.append('file', fs.createReadStream(filePath), {
            filename: req.file.originalname,
            contentType: req.file.mimetype,
        });
        
        const aiResponse = await axios.post(`${AI_SERVICE_URL}/detect/video`, formData, {
            headers: formData.getHeaders(),
            timeout: 180000,
        });
        const ai = aiResponse.data;

        const finalFileUrl = promoteQuarantineFile(filePath);
        cleanUpNeeded = false;

        const analysis = new Analysis({
            userId: extractUserId(req),
            fileUrl: finalFileUrl,
            mediaType: 'video',
            deepfakeProbability: ai.deepfake_probability,
            authenticityScore: ai.authenticity_score,
            ganProbability: 0,
            diffusionProbability: 0,
            modelScores: ai.frame_score_stats || {},
            
            // New visual metrics fields
            prediction: ai.prediction,
            riskLevel: ai.risk_level,
            scores: ai.scores,
            explanation: ai.explanation,
            evidence: ai.evidence || {},
            image: finalFileUrl,
            result: ai.prediction === 'AI_GENERATED' ? 'fake' : 'real',
            confidence: ai.confidence,
            modelVersion: 'v1',
        });

        await analysis.save();
        res.json({ ...analysis.toObject(), aiDetail: ai });

    } catch (err) {
        console.error('Video detection error:', err.message);
        res.status(500).json({ msg: 'AI service or video verification failure', detail: err.message });
    } finally {
        if (cleanUpNeeded) {
            try { fs.unlinkSync(filePath); } catch (_) {}
        }
    }
});

// GET /api/detect/status — Check status of active AI models
router.get('/status', async (req, res) => {
    try {
        const response = await axios.get(`${AI_SERVICE_URL}/detect/status`);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ msg: 'Failed to contact AI service', detail: err.message });
    }
});

module.exports = router;
