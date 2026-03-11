const jwt = require('jsonwebtoken');

module.exports = function(req, res, next) {
    // Get token from header
    const authHeader = req.header('Authorization');
    
    // Check if not token
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ msg: 'No token, authorization denied' });
    }

    const token = authHeader.split(' ')[1];

    if (!process.env.JWT_SECRET) {
        console.error('FATAL ERROR: JWT_SECRET is not defined.');
        return res.status(500).json({ msg: 'Server configuration error' });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user = decoded.user;
        next();
    } catch (err) {
        res.status(401).json({ msg: 'Token is not valid' });
    }
};
