const mongoose = require('mongoose');
const User = require('../models/User');

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/authenticeye';

async function seedAdmin() {
    try {
        await mongoose.connect(MONGO_URI);
        console.log('Connected to MongoDB');

        const adminEmail = 'admin@authenticeye.com';
        
        const existingAdmin = await User.findOne({ email: adminEmail });
        if (existingAdmin) {
            console.log('Admin user already exists!');
            process.exit(0);
        }

        const adminUser = new User({
            name: 'System Admin',
            email: adminEmail,
            password: 'admin123',
            role: 'admin'
        });

        await adminUser.save();
        console.log('Admin user seeded successfully!');
        console.log(`Email: ${adminEmail}`);
        console.log(`Password: admin123`);
        
    } catch (err) {
        console.error('Error seeding admin:', err);
    } finally {
        mongoose.disconnect();
        process.exit(0);
    }
}

seedAdmin();
