import mongoose from "mongoose";

const shipperSchema = new mongoose.Schema({
    shipper_id: {
        type: String,
        required: true,
        unique: true
    },
    name: {
        type: String,
        required: true
    },
    email: {
        type: String,
        required: true,
        unique: true
    },
    phone: {
        type: String,
        required: true,
        unique: true
    },
    password: {
        type: String,
        required: true
    },
    current_location: {
        lat: {
            type: Number,
            required: true,
            default: 10.7769 // Default to HCM City center
        },
        lon: {
            type: Number,
            required: true,
            default: 106.7009
        }
    },
    area: {
        type: String,
        default: 'Ho Chi Minh City'
    },
    status: {
        type: String,
        enum: ['available', 'busy', 'offline'],
        default: 'offline'
    },
    current_order: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'order',
        default: null
    },
    rating: {
        type: Number,
        min: 0,
        max: 5,
        default: 5.0
    },
    total_deliveries: {
        type: Number,
        default: 0
    },
    created_at: {
        type: Date,
        default: Date.now
    },
    last_location_update: {
        type: Date,
        default: Date.now
    },
    vehicle_type: {
        type: String,
        enum: ['motorcycle', 'bicycle', 'car'],
        default: 'motorcycle'
    },
    is_active: {
        type: Boolean,
        default: true
    }
}, { timestamps: true });

// Create index for geospatial queries (for finding nearest shippers)
shipperSchema.index({ 'current_location.lat': 1, 'current_location.lon': 1 });
shipperSchema.index({ status: 1 });

const shipperModel = mongoose.models.shipper || mongoose.model('shipper', shipperSchema);

export default shipperModel;
