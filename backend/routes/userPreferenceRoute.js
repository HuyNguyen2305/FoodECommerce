import express from "express";
import { 
    updateUserFoodPreferences, 
    getUserFoodPreferences, 
    getUserFavorites 
} from "../controllers/userPreferenceController.js";
import auth from "../middleware/auth.js";

const userPreferenceRouter = express.Router();

// Update user food preferences when checkout occurs
// Called from frontend when user proceeds to checkout
userPreferenceRouter.post('/update-preferences', auth, updateUserFoodPreferences);

// Get user's food preferences for recommendation system
userPreferenceRouter.get('/preferences/:userId', getUserFoodPreferences);

// Get user's favorite/most ordered foods
userPreferenceRouter.get('/favorites/:userId', getUserFavorites);

export default userPreferenceRouter;