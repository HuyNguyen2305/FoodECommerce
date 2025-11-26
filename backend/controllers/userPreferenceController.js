import userModel from "../models/userModel.js";
import foodModel from "../models/foodModel.js";

/**
 * User Food Preference Tracking Controller
 * =======================================
 * 
 * Tracks user food preferences for content-based recommendations
 * Updates userFoodData when users proceed to checkout
 */

// Update user food preferences when checkout occurs
const updateUserFoodPreferences = async (req, res) => {
    try {
        const { userId, items } = req.body; // items = [{ _id: food_id, quantity: number }, ...]
        
        if (!userId || !items || !Array.isArray(items)) {
            return res.json({ success: false, message: "Invalid request data" });
        }

        // Get user data
        let userData = await userModel.findById(userId);
        if (!userData) {
            return res.json({ success: false, message: "User not found" });
        }

        // Initialize userFoodData if not exists
        let userFoodData = userData.userFoodData || {
            orderedItems: {},
            preferences: {},
            lastUpdated: null
        };

        // Get food details for the ordered items
        const foodIds = items.map(item => item._id);
        const foods = await foodModel.find({ _id: { $in: foodIds } });
        
        // Create food lookup map
        const foodMap = {};
        foods.forEach(food => {
            foodMap[food._id.toString()] = food;
        });

        // Update ordered items count
        items.forEach(item => {
            const foodId = item._id;
            const quantity = item.quantity || 1;
            
            if (!userFoodData.orderedItems[foodId]) {
                userFoodData.orderedItems[foodId] = 0;
            }
            userFoodData.orderedItems[foodId] += quantity;
        });

        // Update ingredient preferences from food descriptions/ingredients
        items.forEach(item => {
            const food = foodMap[item._id];
            if (food && (food.ingredients || food.description)) {
                // Use ingredients field first, fallback to description
                const ingredientText = food.ingredients || food.description || '';
                
                // Split by comma and clean up each ingredient
                const rawIngredients = ingredientText.split(',').map(ing => ing.trim().toLowerCase());
                const quantity = item.quantity || 1;
                
                rawIngredients.forEach(ingredient => {
                    // Filter out very short words and common non-food words
                    if (ingredient && ingredient.length > 2 && !ingredient.includes('fresh') && !ingredient.includes('served')) {
                        // Clean ingredient (remove extra spaces, numbers, etc.)
                        const cleanIngredient = ingredient.replace(/[^a-zA-Z\s]/g, '').trim();
                        
                        if (cleanIngredient) {
                            if (!userFoodData.preferences[cleanIngredient]) {
                                userFoodData.preferences[cleanIngredient] = 0;
                            }
                            userFoodData.preferences[cleanIngredient] += quantity;
                        }
                    }
                });
            }
        });

        // Update timestamp
        userFoodData.lastUpdated = new Date();

        // Save updated user preferences
        await userModel.findByIdAndUpdate(userId, { userFoodData });

        res.json({ 
            success: true, 
            message: "User food preferences updated",
            itemsProcessed: items.length,
            totalOrders: Object.keys(userFoodData.orderedItems).length
        });

    } catch (error) {
        console.log("Error updating user food preferences:", error);
        res.json({ success: false, message: "Error updating preferences" });
    }
};

// Get user food preferences for recommendation system
const getUserFoodPreferences = async (req, res) => {
    try {
        const { userId } = req.params;
        
        const userData = await userModel.findById(userId);
        if (!userData) {
            return res.json({ success: false, message: "User not found" });
        }

        const userFoodData = userData.userFoodData || {
            orderedItems: {},
            preferences: {},
            lastUpdated: null
        };

        // Calculate preference statistics
        const stats = {
            totalItemsOrdered: Object.keys(userFoodData.orderedItems).length,
            totalOrderCount: Object.values(userFoodData.orderedItems).reduce((sum, count) => sum + count, 0),
            preferredIngredients: Object.entries(userFoodData.preferences)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 15), // Top 15 ingredients from descriptions
            lastUpdated: userFoodData.lastUpdated
        };

        res.json({
            success: true,
            userFoodData,
            stats
        });

    } catch (error) {
        console.log("Error getting user preferences:", error);
        res.json({ success: false, message: "Error fetching preferences" });
    }
};

// Get user's most ordered foods for quick recommendations
const getUserFavorites = async (req, res) => {
    try {
        const { userId } = req.params;
        const limit = parseInt(req.query.limit) || 10;
        
        const userData = await userModel.findById(userId);
        if (!userData) {
            return res.json({ success: false, message: "User not found" });
        }

        const orderedItems = userData.userFoodData?.orderedItems || {};
        
        // Sort by order count and get top items
        const favoriteItems = Object.entries(orderedItems)
            .sort(([,a], [,b]) => b - a)
            .slice(0, limit)
            .map(([foodId, count]) => ({ foodId, orderCount: count }));

        // Get food details for favorites
        const foodIds = favoriteItems.map(item => item.foodId);
        const foods = await foodModel.find({ _id: { $in: foodIds } });
        
        // Combine food details with order counts
        const favorites = favoriteItems.map(item => {
            const food = foods.find(f => f._id.toString() === item.foodId);
            return {
                ...item,
                food: food || null
            };
        }).filter(item => item.food); // Remove items where food wasn't found

        res.json({
            success: true,
            favorites,
            totalFavorites: favorites.length
        });

    } catch (error) {
        console.log("Error getting user favorites:", error);
        res.json({ success: false, message: "Error fetching favorites" });
    }
};

export { 
    updateUserFoodPreferences, 
    getUserFoodPreferences, 
    getUserFavorites 
};