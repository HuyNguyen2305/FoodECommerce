/**
 * Migration Script: Import Test Shippers to MongoDB
 * ==================================================
 * This script imports shippers from shippers_data.json into MongoDB
 * Run this once to populate your database with test data
 */

import mongoose from 'mongoose';
import fs from 'fs';
import path from 'path';
import bcrypt from 'bcrypt';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config();

// Import shipper model
const shipperSchema = new mongoose.Schema({
    shipper_id: { type: String, required: true, unique: true },
    name: { type: String, required: true },
    email: { type: String, required: true, unique: true },
    phone: { type: String, required: true, unique: true },
    password: { type: String, required: true },
    current_location: {
        lat: { type: Number, required: true, default: 10.7769 },
        lon: { type: Number, required: true, default: 106.7009 }
    },
    area: { type: String, default: 'Ho Chi Minh City' },
    status: { type: String, enum: ['available', 'busy', 'offline'], default: 'offline' },
    current_order: { type: mongoose.Schema.Types.ObjectId, ref: 'order', default: null },
    rating: { type: Number, min: 0, max: 5, default: 5.0 },
    total_deliveries: { type: Number, default: 0 },
    created_at: { type: Date, default: Date.now },
    last_location_update: { type: Date, default: Date.now },
    vehicle_type: { type: String, enum: ['motorcycle', 'bicycle', 'car'], default: 'motorcycle' },
    is_active: { type: Boolean, default: true }
}, { timestamps: true });

const Shipper = mongoose.model('shipper', shipperSchema);

async function importShippers() {
    try {
        // Connect to MongoDB
        console.log('🔌 Connecting to MongoDB...');
        await mongoose.connect('mongodb+srv://huyworkandcontact_db_user:Slenderman23*@cluster0.9vsew15.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0');
        console.log('✅ Connected to MongoDB');

        // Read JSON file
        const jsonPath = path.join(__dirname, '../RoutingService/shippers_data.json');
        const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const shippers = jsonData.shippers;

        console.log(`📂 Found ${shippers.length} shippers in JSON file`);

        // Default password for all test shippers
        const defaultPassword = 'shipper123';
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(defaultPassword, salt);

        let imported = 0;
        let skipped = 0;

        for (const shipper of shippers) {
            try {
                // Check if shipper already exists
                const exists = await Shipper.findOne({ shipper_id: shipper.shipper_id });
                
                if (exists) {
                    console.log(`⏭️  Skipped ${shipper.shipper_id} - already exists`);
                    skipped++;
                    continue;
                }

                // Create email from shipper_id
                const email = `${shipper.shipper_id.toLowerCase()}@shipper.local`;

                // Create new shipper document
                const newShipper = new Shipper({
                    shipper_id: shipper.shipper_id,
                    name: shipper.name,
                    email: email,
                    phone: shipper.phone,
                    password: hashedPassword,
                    current_location: shipper.current_location,
                    area: shipper.area,
                    status: shipper.status,
                    rating: shipper.rating,
                    total_deliveries: shipper.total_deliveries,
                    created_at: shipper.created_at,
                    last_location_update: shipper.last_update || shipper.created_at
                });

                await newShipper.save();
                console.log(`✅ Imported ${shipper.shipper_id} - ${shipper.name}`);
                imported++;

            } catch (error) {
                console.error(`❌ Error importing ${shipper.shipper_id}:`, error.message);
            }
        }

        console.log('\n📊 Import Summary:');
        console.log(`   ✅ Imported: ${imported}`);
        console.log(`   ⏭️  Skipped: ${skipped}`);
        console.log(`   📝 Total: ${shippers.length}`);
        console.log('\n🔐 Default Password for all test shippers: shipper123');
        console.log('📧 Email format: ship0001@shipper.local, ship0002@shipper.local, etc.\n');

        // Disconnect
        await mongoose.disconnect();
        console.log('👋 Disconnected from MongoDB');

    } catch (error) {
        console.error('❌ Migration failed:', error);
        process.exit(1);
    }
}

// Run migration
importShippers();
