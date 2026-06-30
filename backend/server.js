require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const path = require('path');
const mongoSanitize = require('express-mongo-sanitize');
const client = require('prom-client');
const cookieParser = require('cookie-parser');

// ─── Sentry Initializer (Phase 11) ──────────────────────────────────────────
const Sentry = require('@sentry/node');
if (process.env.SENTRY_DSN) {
    Sentry.init({ dsn: process.env.SENTRY_DSN });
    console.log('✅ Sentry monitoring initiated');
}

const authRoutes = require('./routes/auth');
const detectRoutes = require('./routes/detect');
const historyRoutes = require('./routes/history');
const feedbackRoutes = require('./routes/feedback');
const adminRoutes = require('./routes/admin');

const app = express();

if (process.env.SENTRY_DSN) {
    app.use(Sentry.Handlers.requestHandler());
}

// ─── Security Middleware & CSP Headers (Phase 10) ───────────────────────────
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            connectSrc: ["'self'", "http://localhost:5000", "http://localhost:8000", "ws://localhost:5173", "http://localhost:5173"],
            imgSrc: ["'self'", "data:", "blob:", "http://localhost:5000", "https://*"],
            scriptSrc: ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            fontSrc: ["'self'", "https://fonts.gstatic.com"],
        }
    }
}));

app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:5173',
    credentials: true,
}));

app.use(cookieParser());

const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

app.use(express.json());

// Input Sanitization against SQL/NoSQL Injection
app.use(mongoSanitize());

app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// ─── Prometheus Monitoring Exporter (Phase 11) ──────────────────────────────
const collectDefaultMetrics = client.collectDefaultMetrics;
collectDefaultMetrics({ register: client.register });

const httpRequestCounter = new client.Counter({
    name: 'http_requests_total',
    help: 'Total HTTP requests received',
    labelNames: ['method', 'route', 'status']
});

app.use((req, res, next) => {
    res.on('finish', () => {
        httpRequestCounter.inc({
            method: req.method,
            route: req.route ? req.route.path : req.path,
            status: res.statusCode
        });
    });
    next();
});

app.get('/metrics', async (req, res) => {
    res.set('Content-Type', client.register.contentType);
    res.send(await client.register.metrics());
});

// ─── Routes ───────────────────────────────────────────────────────────────────
app.use('/api/auth', authRoutes);
app.use('/api/detect', detectRoutes);
app.use('/api/history', historyRoutes);
app.use('/api/feedback', feedbackRoutes);
app.use('/api/admin', adminRoutes);

// Sentry Error Handler
if (process.env.SENTRY_DSN) {
    app.use(Sentry.Handlers.errorHandler());
}

// ─── Health Check ─────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
    res.json({ status: 'AuthenticEye Backend v4.0 running', version: '4.0.0' });
});

// ─── Database Connection ───────────────────────────────────────────────────────
mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/authenticeye')
    .then(() => console.log('✅ MongoDB Connected'))
    .catch(err => console.error('❌ MongoDB connection error:', err));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`🚀 AuthenticEye Backend running on port ${PORT}`);
});
