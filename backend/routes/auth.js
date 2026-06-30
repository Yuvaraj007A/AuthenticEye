const express = require('express');
const router = express.Router();
const User = require('../models/User');
const jwt = require('jsonwebtoken');

// @route   POST api/auth/register
// @desc    Register user
// @access  Public
router.post('/register', async (req, res) => {
    const { name, email, password } = req.body;
    try {
        let user = await User.findOne({ email });
        if (user) return res.status(400).json({ msg: 'User already exists' });

        user = new User({ name, email, password });
        await user.save();

        const payload = { user: { id: user.id, role: user.role } };
        const accessToken = jwt.sign(payload, process.env.JWT_SECRET || 'secret_key', { expiresIn: '15m' });
        const refreshToken = jwt.sign(payload, process.env.JWT_REFRESH_SECRET || 'refresh_secret_key', { expiresIn: '7d' });

        res.cookie('refreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
        });

        res.json({ token: accessToken, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
    } catch (err) {
        console.error(err.message);
        res.status(500).send('Server error');
    }
});

// @route   POST api/auth/login
// @desc    Authenticate user & get token
// @access  Public
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    try {
        let user = await User.findOne({ email });
        if (!user) return res.status(400).json({ msg: 'Invalid Credentials' });

        const isMatch = await user.comparePassword(password);
        if (!isMatch) return res.status(400).json({ msg: 'Invalid Credentials' });

        const payload = { user: { id: user.id, role: user.role } };
        const accessToken = jwt.sign(payload, process.env.JWT_SECRET || 'secret_key', { expiresIn: '15m' });
        const refreshToken = jwt.sign(payload, process.env.JWT_REFRESH_SECRET || 'refresh_secret_key', { expiresIn: '7d' });

        res.cookie('refreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
        });

        res.json({ token: accessToken, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
    } catch (err) {
        console.error(err.message);
        res.status(500).send('Server error');
    }
});

// @route   POST api/auth/refresh-token
// @desc    Verify refresh token and issue new access token
// @access  Public
router.post('/refresh-token', (req, res) => {
    const refreshToken = req.cookies.refreshToken;
    if (!refreshToken) {
        return res.status(401).json({ msg: 'No refresh token, authorization denied' });
    }
    try {
        const decoded = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET || 'refresh_secret_key');
        const payload = { user: { id: decoded.user.id, role: decoded.user.role } };
        const accessToken = jwt.sign(payload, process.env.JWT_SECRET || 'secret_key', { expiresIn: '15m' });
        res.json({ token: accessToken });
    } catch (err) {
        res.status(401).json({ msg: 'Refresh token is not valid' });
    }
});

// @route   POST api/auth/logout
// @desc    Clear refresh token cookies
// @access  Public
router.post('/logout', (req, res) => {
    res.clearCookie('refreshToken');
    res.json({ msg: 'Logged out successfully' });
});

module.exports = router;
