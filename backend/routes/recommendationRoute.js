// Recommendation Routes - Connect Node.js with Python ML Service
import express from 'express';
import {
    getRecommendations,
    trackClick,
    trackOrder,
    trackRating,
    getServiceHealth,
    getStats
} from '../controllers/recommendationController.js';

const recommendationRouter = express.Router();

// Get personalized recommendations for a user
recommendationRouter.post('/recommend/:userId', getRecommendations);

// Track user interactions with recommendations
recommendationRouter.post('/track/click', trackClick);
recommendationRouter.post('/track/order', trackOrder);
recommendationRouter.post('/track/rating', trackRating);

// System health and statistics
recommendationRouter.get('/health', getServiceHealth);
recommendationRouter.get('/stats', getStats);

export default recommendationRouter;