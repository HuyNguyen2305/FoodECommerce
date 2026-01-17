// Recommendation Controller - Integrates with Python ML Service
import axios from 'axios';
import Food from '../models/foodModel.js';

// Python ML Service Configuration
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';
const ML_SERVICE_TIMEOUT = 5000; // 5 second timeout

class RecommendationController {
    constructor() {
        this.mlServiceUrl = ML_SERVICE_URL;
        console.log(`Recommendation service configured for: ${this.mlServiceUrl}`);
    }

    // Get personalized food recommendations
    async getRecommendations(req, res) {
        try {
            const { userId } = req.params;
            const { count = 8, sessionId, hour } = req.body;

            // Handle neutral users (no login) - use cold start recommendations
            if (!userId || userId === 'null' || userId === 'undefined') {
                console.log(`Getting cold-start recommendations for neutral user, count: ${count}`);
                
                try {
                    const currentHour = hour || new Date().getHours();
                    const mlResponse = await axios.get(`${this.mlServiceUrl}/content-based/cold-start`, {
                        params: {
                            count: parseInt(count),
                            hour: currentHour
                        },
                        timeout: ML_SERVICE_TIMEOUT,
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });

                    const recommendations = mlResponse.data;

                    if (recommendations.success) {
                        console.log(`Cold-start ML service returned ${recommendations.count} recommendations`);
                        return res.json({
                            success: true,
                            recommendations: recommendations.recommendations,
                            strategy: recommendations.strategy,
                            hour: recommendations.hour,
                            message: 'Time-based recommendations for you',
                            isNeutralUser: true
                        });
                    }
                } catch (mlError) {
                    console.log('Cold-start ML service unavailable:', mlError.message);
                    // Fallback to Node.js time-based recommendations
                    const fallbackRecommendations = await this.getFallbackRecommendations(count);
                    return res.json({
                        success: true,
                        recommendations: fallbackRecommendations,
                        fallback: true,
                        message: 'Recommendations based on current time',
                        isNeutralUser: true,
                        context: { meal_time: this.getCurrentMealTime() }
                    });
                }
            }

            console.log(`Getting personalized recommendations for user: ${userId}, count: ${count}`);

            // Try Python ML service for logged-in users
            try {
                const mlResponse = await axios.post(`${this.mlServiceUrl}/recommend`, {
                    user_id: userId,
                    count: parseInt(count),
                    session_id: sessionId || this.generateSessionId()
                }, {
                    timeout: ML_SERVICE_TIMEOUT,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const recommendations = mlResponse.data;

                if (recommendations.success) {
                    console.log(`ML service returned ${recommendations.count} recommendations`);
                    return res.json({
                        success: true,
                        recommendations: recommendations.recommendations,
                        context: recommendations.context,
                        message: `Got ${recommendations.count} AI-powered recommendations`,
                        isNeutralUser: false
                    });
                }
            } catch (mlError) {
                console.log('ML service unavailable:', mlError.message);
            }

            // Fallback to smart recommendations if ML service fails
            const fallbackRecommendations = await this.getFallbackRecommendations(count);
            
            res.json({
                success: true,
                recommendations: fallbackRecommendations,
                fallback: true,
                message: 'Using smart fallback recommendations',
                context: { meal_time: this.getCurrentMealTime() }
            });

        } catch (error) {
            console.error('Error in getRecommendations:', error);
            
            // Last resort: simple random recommendations
            try {
                const simpleRecommendations = await this.getSimpleRecommendations(8);
                res.json({
                    success: true,
                    recommendations: simpleRecommendations,
                    fallback: true,
                    message: 'Using basic recommendations'
                });
            } catch (finalError) {
                console.error('Final fallback failed:', finalError);
                res.status(500).json({
                    success: false,
                    error: 'Unable to generate recommendations',
                    details: finalError.message
                });
            }
        }
    }

    // Track user click on recommended item
    async trackClick(req, res) {
        try {
            const { userId, foodId, position, sessionId } = req.body;

            if (!userId || !foodId) {
                return res.status(400).json({
                    success: false,
                    error: 'userId and foodId are required'
                });
            }

            // Call Python ML service to track click
            await axios.post(`${this.mlServiceUrl}/track/click`, {
                user_id: userId,
                food_id: foodId,
                position: position,
                session_id: sessionId
            }, {
                timeout: ML_SERVICE_TIMEOUT
            });

            res.json({
                success: true,
                message: 'Click tracked successfully'
            });

        } catch (error) {
            console.error('Error tracking click:', error.message);
            // Don't fail the request if tracking fails
            res.json({
                success: true,
                message: 'Click received (tracking service unavailable)'
            });
        }
    }

    // Track user order
    async trackOrder(req, res) {
        try {
            const { userId, foodItems, orderValue, sessionId } = req.body;

            if (!userId || !foodItems || !Array.isArray(foodItems)) {
                return res.status(400).json({
                    success: false,
                    error: 'userId and foodItems array are required'
                });
            }

            // Call Python ML service to track order
            await axios.post(`${this.mlServiceUrl}/track/order`, {
                user_id: userId,
                food_items: foodItems,
                order_value: orderValue || 0,
                session_id: sessionId
            }, {
                timeout: ML_SERVICE_TIMEOUT
            });

            res.json({
                success: true,
                message: `Order tracked successfully for ${foodItems.length} items`
            });

        } catch (error) {
            console.error('Error tracking order:', error.message);
            // Don't fail the order if tracking fails
            res.json({
                success: true,
                message: 'Order received (tracking service unavailable)'
            });
        }
    }

    // Track user rating
    async trackRating(req, res) {
        try {
            const { userId, foodId, rating, reviewText, sessionId } = req.body;

            if (!userId || !foodId || rating === undefined) {
                return res.status(400).json({
                    success: false,
                    error: 'userId, foodId, and rating are required'
                });
            }

            if (rating < 1 || rating > 5) {
                return res.status(400).json({
                    success: false,
                    error: 'Rating must be between 1 and 5'
                });
            }

            // Call Python ML service to track rating
            await axios.post(`${this.mlServiceUrl}/track/rating`, {
                user_id: userId,
                food_id: foodId,
                rating: rating,
                review_text: reviewText,
                session_id: sessionId
            }, {
                timeout: ML_SERVICE_TIMEOUT
            });

            res.json({
                success: true,
                message: 'Rating tracked successfully'
            });

        } catch (error) {
            console.error('Error tracking rating:', error.message);
            // Don't fail the request if tracking fails
            res.json({
                success: true,
                message: 'Rating received (tracking service unavailable)'
            });
        }
    }

    // Get ML service health status
    async getServiceHealth(req, res) {
        try {
            const healthResponse = await axios.get(`${this.mlServiceUrl}/health`, {
                timeout: 3000
            });

            res.json({
                success: true,
                ml_service: healthResponse.data,
                connection: 'healthy'
            });

        } catch (error) {
            res.json({
                success: false,
                error: 'ML service unavailable',
                details: error.message
            });
        }
    }

    // Get recommendation system statistics
    async getStats(req, res) {
        try {
            const statsResponse = await axios.get(`${this.mlServiceUrl}/stats`, {
                timeout: ML_SERVICE_TIMEOUT
            });

            res.json({
                success: true,
                stats: statsResponse.data
            });

        } catch (error) {
            console.error('Error getting stats:', error.message);
            res.status(500).json({
                success: false,
                error: 'Unable to retrieve recommendation statistics'
            });
        }
    }

    // Fallback recommendations when ML service is unavailable
    async getFallbackRecommendations(count = 8) {
        try {
            console.log('Generating fallback recommendations...');
            
            // Get popular foods based on current time
            const currentHour = new Date().getHours();
            const mealTime = this.getCurrentMealTime();
            
            let categoryFilter = {};

            // Smart time-based filtering
            if (currentHour >= 5 && currentHour < 11) {
                categoryFilter = { category: { $in: ['Noodle', 'Salad', 'Vegan'] } };
            } else if (currentHour >= 11 && currentHour < 16) {
                categoryFilter = { category: { $in: ['Rice', 'Noodle', 'Salad', 'Vegan'] } };
            } else {
                categoryFilter = { category: { $in: ['Rice', 'Seafood', 'Noodle'] } };
            }

            const foods = await Food.find(categoryFilter).limit(count);
            
            console.log(`Found ${foods.length} foods for fallback recommendations`);
            
            return foods.map((food, index) => ({
                food_id: food._id.toString(),
                name: food.name,
                category: food.category,
                price: food.price,
                image: food.image,
                score: 0.7 - (index * 0.1), // Decreasing scores
                position: index + 1,
                explanation: this.getFallbackExplanation(mealTime, food.category)
            }));

        } catch (error) {
            console.error('Error getting fallback recommendations:', error.message);
            throw new Error('Fallback recommendation generation failed');
        }
    }

    // Simple recommendations as last resort
    async getSimpleRecommendations(count = 8) {
        try {
            console.log('Generating simple recommendations...');
            
            const foods = await Food.find({}).limit(count);
            
            return foods.map((food, index) => ({
                food_id: food._id.toString(),
                name: food.name,
                category: food.category,
                price: food.price,
                image: food.image,
                score: 0.5,
                position: index + 1,
                explanation: 'Popular choice'
            }));

        } catch (error) {
            console.error('Error getting simple recommendations:', error.message);
            throw new Error('Simple recommendation generation failed');
        }
    }

    // Get current meal time
    getCurrentMealTime() {
        const hour = new Date().getHours();
        if (hour >= 5 && hour < 11) return 'breakfast';
        if (hour >= 11 && hour < 16) return 'lunch';
        if (hour >= 16 && hour < 22) return 'dinner';
        return 'late_night';
    }

    // Generate explanation for fallback recommendations
    getFallbackExplanation(mealTime, category) {
        const explanations = {
            breakfast: {
                'Noodle': 'Perfect for breakfast',
                'Salad': 'Fresh and light',
                'Vegan': 'Healthy start to your day'
            },
            lunch: {
                'Rice': 'Satisfying lunch choice',
                'Noodle': 'Quick and delicious',
                'Salad': 'Light and nutritious',
                'Vegan': 'Healthy and balanced'
            },
            dinner: {
                'Rice': 'Hearty dinner option',
                'Seafood': 'Premium quality',
                'Noodle': 'Comforting meal'
            }
        };

        return explanations[mealTime]?.[category] || 'Recommended for you';
    }

    // Generate session ID for tracking
    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Create singleton instance
const recommendationController = new RecommendationController();

// Export route handlers
export const getRecommendations = (req, res) => recommendationController.getRecommendations(req, res);
export const trackClick = (req, res) => recommendationController.trackClick(req, res);
export const trackOrder = (req, res) => recommendationController.trackOrder(req, res);
export const trackRating = (req, res) => recommendationController.trackRating(req, res);
export const getServiceHealth = (req, res) => recommendationController.getServiceHealth(req, res);
export const getStats = (req, res) => recommendationController.getStats(req, res);