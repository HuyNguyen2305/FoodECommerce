import express from 'express';
import { 
    loginShipper, 
    registerShipper, 
    getShipperProfile,
    updateLocation,
    updateStatus,
    getAvailableShippers,
    assignOrder,
    completeDelivery,
    updateRating
} from '../controllers/shipperController.js';
import authMiddleware from '../middleware/auth.js';

const shipperRouter = express.Router();

// Public routes
shipperRouter.post('/register', registerShipper);
shipperRouter.post('/login', loginShipper);

// Protected routes (require authentication)
shipperRouter.get('/profile', authMiddleware, getShipperProfile);
shipperRouter.post('/update-location', authMiddleware, updateLocation);
shipperRouter.post('/update-status', authMiddleware, updateStatus);
shipperRouter.post('/complete-delivery', authMiddleware, completeDelivery);

// Admin/Dispatcher routes
shipperRouter.get('/available', getAvailableShippers);
shipperRouter.post('/assign-order', assignOrder);
shipperRouter.post('/update-rating', updateRating);

// Get all shippers (for dashboard/dispatcher)
shipperRouter.get('/all', async (req, res) => {
    try {
        const shipperModel = (await import('../models/shipperModel.js')).default;
        const shippers = await shipperModel.find({ is_active: true }).select('-password');
        
        // Format for dispatcher compatibility
        const formattedShippers = shippers.map(s => ({
            shipper_id: s.shipper_id,
            name: s.name,
            phone: s.phone,
            current_location: s.current_location,
            area: s.area,
            status: s.status,
            current_order: s.current_order,
            total_deliveries: s.total_deliveries,
            rating: s.rating,
            created_at: s.created_at,
            last_update: s.last_location_update
        }));

        res.json({ 
            success: true, 
            shippers: formattedShippers,
            total: formattedShippers.length 
        });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error fetching shippers" });
    }
});

export default shipperRouter;
