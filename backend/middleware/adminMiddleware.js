module.exports = function(req, res, next) {
    if (!req.user) {
        return res.status(401).json({ msg: 'Authorization required' });
    }
    
    if (req.user.role !== 'admin') {
        return res.status(403).json({ msg: 'Access denied: Admins only' });
    }
    
    next();
};
