import React, { useContext, useState, useEffect } from 'react'
import './RecommendedFood.css'
import { StoreContext } from '../../context/StoreContext'
import FoodItem from '../FoodItem/FoodItem'
import axios from 'axios'

const RecommendedFood = () => {

    const { food_list, url, token } = useContext(StoreContext)
    const [recommendedItems, setRecommendedItems] = useState([])
    const [loading, setLoading] = useState(true)
    const [sessionId] = useState(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

    // Get user ID from context or generate guest ID
    const getUserId = () => {
        if (token) {
            try {
                // Decode JWT token to get actual user ID
                const base64Url = token.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const payload = JSON.parse(window.atob(base64));
                return payload.id || payload.userId || `user_${Date.now()}`;
            } catch (error) {
                console.error('Error decoding token:', error);
                return `user_${Date.now()}`;
            }
        }
        // For guests, use consistent ID based on session
        const guestId = localStorage.getItem('guestId');
        if (guestId) {
            return guestId;
        }
        const newGuestId = `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('guestId', newGuestId);
        return newGuestId;
    };

    // Get smart recommendations using ML model
    const fetchRecommendations = async () => {
        try {
            setLoading(true);
            
            // Call Python ML recommendation API
            const userId = getUserId();
            const response = await axios.post('http://localhost:8000/recommend', {
                user_id: userId,
                count: 8,
                session_id: sessionId
            });
            
            if (response.data.success && response.data.recommendations) {
                // Map recommendations to food items from food_list
                const mlRecommendations = response.data.recommendations
                    .map(rec => {
                        const foodItem = food_list.find(f => f._id === rec.food_id || f.name.toLowerCase() === rec.name.toLowerCase());
                        if (foodItem) {
                            return {
                                ...foodItem,
                                ml_score: rec.score,
                                explanation: rec.explanation
                            };
                        }
                        return null;
                    })
                    .filter(item => item !== null);
                
                if (mlRecommendations.length > 0) {
                    setRecommendedItems(mlRecommendations);
                    console.log('✅ ML Recommendations loaded:', mlRecommendations.length);
                    return;
                }
            }
            
            // Fallback if ML service fails
            console.log('⚠️ ML service unavailable, using fallback');
            getFallbackRecommendations();
            
        } catch (error) {
            console.log('⚠️ Error getting ML recommendations:', error.message);
            getFallbackRecommendations();
        } finally {
            setLoading(false);
        }
    };

    // Fallback: Smart recommendation logic based on time (used if ML service is down)
    const getFallbackRecommendations = () => {
        const currentHour = new Date().getHours();
        const isWeekend = new Date().getDay() === 0 || new Date().getDay() === 6;
        
        // Time-based meal preferences (based on nutrition and appetite patterns)
        let mealTimeWeights = {};
        
        if (currentHour >= 5 && currentHour < 11) { // Breakfast/Morning
            mealTimeWeights = { 
                'Noodle': 3, 'Salad': 3, 'Vegan': 2, 'Rice': 1, 'Seafood': 1, 'Desserts': 1, 'Sandwich': 2, 'Pasta': 2 
            };
        } else if (currentHour >= 11 && currentHour < 16) { // Lunch
            mealTimeWeights = { 
                'Rice': 3, 'Noodle': 3, 'Salad': 2, 'Seafood': 2, 'Vegan': 2, 'Sandwich': 2, 'Pasta': 2, 'Desserts': 1 
            };
        } else if (currentHour >= 16 && currentHour < 22) { // Dinner
            mealTimeWeights = { 
                'Rice': 3, 'Seafood': 3, 'Noodle': 2, 'Pasta': 2, 'Vegan': 2, 'Salad': 1, 'Sandwich': 1, 'Desserts': 2 
            };
        } else { // Late night/Early morning
            mealTimeWeights = { 
                'Noodle': 2, 'Salad': 2, 'Sandwich': 2, 'Desserts': 1, 'Rice': 1, 'Seafood': 1, 'Vegan': 2, 'Pasta': 1 
            };
        }

        // Create weighted food list
        const weightedFoods = food_list.map(food => {
            const categoryWeight = mealTimeWeights[food.category] || 1;
            const varietyBonus = Math.random() * 0.5; // Add randomness for variety
            const weekendBonus = isWeekend ? 0.2 : 0; // Slightly different preferences on weekends
            
            return {
                ...food,
                recommendationScore: categoryWeight + varietyBonus + weekendBonus
            };
        });

        // Sort by recommendation score and ensure variety
        weightedFoods.sort((a, b) => b.recommendationScore - a.recommendationScore);

        // Select recommendations ensuring category diversity
        const selectedItems = [];
        const usedCategories = new Set();
        const maxPerCategory = 2; // Max 2 items per category for variety

        // First pass: Pick top items with category limits
        for (const food of weightedFoods) {
            if (selectedItems.length >= 8) break;
            
            const categoryCount = selectedItems.filter(item => item.category === food.category).length;
            if (categoryCount < maxPerCategory) {
                selectedItems.push(food);
                usedCategories.add(food.category);
            }
        }

        // Second pass: Fill remaining slots if needed
        if (selectedItems.length < 8) {
            for (const food of weightedFoods) {
                if (selectedItems.length >= 8) break;
                if (!selectedItems.some(item => item._id === food._id)) {
                    selectedItems.push(food);
                }
            }
        }

        setRecommendedItems(selectedItems.slice(0, 8));
    };

    // Track click on recommended item (simplified)
    const handleRecommendationClick = async (foodId, position) => {
        console.log(`User clicked on recommended food: ${foodId} at position ${position}`);
        // Future enhancement: Store click data in localStorage or send to analytics
    };

    // Fetch recommendations when component mounts or food_list changes
    useEffect(() => {
        if (food_list && food_list.length > 0) {
            fetchRecommendations();
        }
    }, [food_list]);

    if (loading) {
        return (
            <div className='recommended-food' id='recommended-food'>
                <h2>Recommended for you</h2>
                <p className='recommended-subtitle'>Loading personalized recommendations...</p>
                <div className="recommended-food-list">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((_, index) => (
                        <div key={index} className="food-item-skeleton">
                            <div className="skeleton-image"></div>
                            <div className="skeleton-text"></div>
                            <div className="skeleton-text short"></div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className='recommended-food' id='recommended-food'>
            <h2>Recommended for you</h2>
            <p className='recommended-subtitle'>
                {recommendedItems.length > 0 
                    ? 'Recommendations for your appetite'
                    : 'Popular choices for you'
                }
            </p>
            <div className="recommended-food-list">
                {recommendedItems.map((item, index) => {
                    return <FoodItem 
                        key={index} 
                        id={item._id} 
                        name={item.name} 
                        description={item.description} 
                        price={item.price} 
                        image={item.image}
                        onClick={() => handleRecommendationClick(item._id, index + 1)}
                    />
                })}
            </div>
            {recommendedItems.length === 0 && (
                <p className="no-recommendations">
                    No recommendations available at the moment. Please try again later.
                </p>
            )}
        </div>
    )
}

export default RecommendedFood