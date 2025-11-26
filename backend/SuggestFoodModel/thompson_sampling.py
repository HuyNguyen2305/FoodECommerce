# Thompson Sampling Algorithm for Food Recommendations
import numpy as np
from collections import defaultdict
import json
import logging
from datetime import datetime
from database import get_food_database

logger = logging.getLogger(__name__)

class ThompsonSampling:
    """
    Thompson Sampling implementation for food delivery recommendations
    Uses Beta distribution to balance exploration vs exploitation for food recommendations
    """
    
    def __init__(self, alpha_prior=1.0, beta_prior=1.0):
        """
        Initialize Thompson Sampling with Beta distribution priors
        
        Args:
            alpha_prior: Prior successes (positive interactions)
            beta_prior: Prior failures (negative interactions)
        """
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        
        # Item statistics: {food_id: {context: {successes, failures}}}
        self.item_stats = defaultdict(lambda: defaultdict(lambda: {
            'successes': alpha_prior, 
            'failures': beta_prior,
            'total_interactions': 0,
            'last_updated': datetime.now()
        }))
        
        # Context weights for food patterns
        self.context_weights = {
            'meal_time': 0.4,    # Strong influence (breakfast items in morning)
            'weather': 0.3,      # Medium influence (soup on rainy days)
            'user_history': 0.2, # User preferences
            'popularity': 0.1    # Trending items
        }
        
        self.db = get_food_database()
        logger.info("Thompson Sampling initialized for food recommendations")
    
    def _get_context_key(self, context):
        """Generate context key for storing statistics"""
        if not context:
            return 'general'
        
        # Create context signature
        context_parts = []
        for key in ['meal_time', 'weather', 'region', 'user_type']:
            if key in context:
                context_parts.append(f"{key}:{context[key]}")
        
        return '|'.join(context_parts) if context_parts else 'general'
    
    def update_reward(self, food_id, context, reward_value, interaction_type='click'):
        """
        Update Thompson Sampling statistics based on user interaction
        
        Args:
            food_id: ID of the food item
            context: Context dictionary (meal_time, weather, etc.)
            reward_value: Reward value (0-1 for clicks, 0-5 for ratings)
            interaction_type: Type of interaction (click, order, rating)
        """
        try:
            context_key = self._get_context_key(context)
            
            # Normalize reward based on interaction type
            if interaction_type == 'click':
                success = reward_value > 0  # Click = success
            elif interaction_type == 'order':
                success = True  # Order is always a strong positive signal
                reward_value = min(reward_value * 2, 1.0)  # Boost order rewards
            elif interaction_type == 'rating':
                success = reward_value >= 3  # Rating 3+ = success
                reward_value = reward_value / 5.0  # Normalize to 0-1
            else:
                success = reward_value > 0.5
            
            # Update statistics
            stats = self.item_stats[food_id][context_key]
            
            if success:
                stats['successes'] += reward_value
            else:
                stats['failures'] += (1 - reward_value)
            
            stats['total_interactions'] += 1
            stats['last_updated'] = datetime.now()
            
            logger.info(f"Updated {food_id} in context {context_key}: reward={reward_value}, type={interaction_type}")
            
        except Exception as e:
            logger.error(f"Error updating reward: {e}")
    
    def _sample_beta_score(self, food_id, context_key):
        """Sample score from Beta distribution for Thompson Sampling"""
        try:
            stats = self.item_stats[food_id][context_key]
            alpha = stats['successes']
            beta = stats['failures']
            
            # Sample from Beta distribution
            score = np.random.beta(alpha, beta)
            
            return score
        except Exception as e:
            logger.error(f"Error sampling beta score: {e}")
            return np.random.beta(self.alpha_prior, self.beta_prior)
    
    def _apply_smart_context_boost(self, food_items, context):
        """Apply intelligent context boosts based on data-driven factors"""
        boosted_items = {}
        
        try:
            meal_time = context.get('meal_time', '')
            user_id = context.get('user_id')
            
            for food in food_items:
                food_id = str(food['_id'])
                category = food.get('category', '').lower()
                name = food.get('name', '').lower()
                price = food.get('price', 0)
                
                boost = 1.0  # Base multiplier
                
                # 1. NUTRITIONAL & MEAL TIME INTELLIGENCE
                boost *= self._get_meal_time_boost(meal_time, category, name)
                
                # 2. POPULARITY & ORDER FREQUENCY BOOST
                boost *= self._get_popularity_boost(food_id)
                
                # 3. PRICE OPTIMIZATION (sweet spot pricing)
                boost *= self._get_price_optimization_boost(price)
                
                # 4. CATEGORY VARIETY BOOST (avoid recommendation monotony)
                boost *= self._get_variety_boost(category, food_items)
                
                # 5. USER PREFERENCE LEARNING BOOST
                if user_id:
                    boost *= self._get_user_preference_boost(user_id, food)
                
                boosted_items[food_id] = {'food': food, 'boost': boost}
            
        except Exception as e:
            logger.error(f"Error applying smart context boost: {e}")
            # Fallback: return items without boost
            for food in food_items:
                food_id = str(food['_id'])
                boosted_items[food_id] = {'food': food, 'boost': 1.0}
        
        return boosted_items
    
    def _get_meal_time_boost(self, meal_time, category, name):
        """Data-driven meal time preferences based on nutrition and practicality"""
        if meal_time == 'breakfast':
            # Light, energizing foods for morning
            if any(word in name.lower() for word in ['light', 'fresh', 'salad', 'noodle']):
                return 1.3
            elif category in ['salad', 'vegan']:
                return 1.2
        elif meal_time == 'lunch':
            # Balanced, satisfying meals for midday energy
            if category in ['rice', 'noodle', 'salad']:
                return 1.2
            elif any(word in name.lower() for word in ['bowl', 'combo', 'set']):
                return 1.1
        elif meal_time == 'dinner':
            # Hearty, satisfying foods for evening
            if category in ['rice', 'seafood']:
                return 1.2
            elif any(word in name.lower() for word in ['family', 'sharing', 'large']):
                return 1.1
        return 1.0
    
    def _get_popularity_boost(self, food_id):
        """Boost based on actual order frequency and ratings"""
        try:
            # Get interaction stats for this food item
            stats = self.db.get_interaction_stats(food_id)
            
            # Convert success rate to boost (0.0-2.0 range)
            success_rate = stats.get('success_rate', 0)
            avg_rating = stats.get('avg_rating', 0)
            order_count = stats.get('orders', 0)
            
            # Combine multiple factors for popularity boost
            popularity_boost = 1.0
            
            # Success rate boost (clicks/orders vs views)
            if success_rate > 0.3:  # High engagement
                popularity_boost *= 1.3
            elif success_rate > 0.1:  # Medium engagement  
                popularity_boost *= 1.1
            
            # Rating boost
            if avg_rating >= 4.5:
                popularity_boost *= 1.4
            elif avg_rating >= 4.0:
                popularity_boost *= 1.2
            elif avg_rating >= 3.5:
                popularity_boost *= 1.1
            
            # Order frequency boost (trending items)
            if order_count > 50:  # Very popular
                popularity_boost *= 1.3
            elif order_count > 20:  # Popular
                popularity_boost *= 1.1
            
            return min(popularity_boost, 2.0)  # Cap at 2x boost
            
        except Exception as e:
            logger.error(f"Error calculating popularity boost: {e}")
            return 1.0
    
    def _get_price_optimization_boost(self, price):
        """Optimize for price points that convert well"""
        try:
            # Convert VND price ranges to boost factors
            # Based on typical food delivery price psychology
            
            if 50000 <= price <= 150000:  # Sweet spot for individual meals
                return 1.2
            elif 150000 <= price <= 250000:  # Premium but accessible
                return 1.1
            elif 30000 <= price <= 50000:  # Budget-friendly options
                return 1.1
            elif price > 300000:  # High-end items (lower boost)
                return 0.9
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating price boost: {e}")
            return 1.0
    
    def _get_variety_boost(self, category, all_items):
        """Ensure recommendation diversity to avoid monotony"""
        try:
            # Count how many items of this category are in the recommendation set
            category_count = sum(1 for item in all_items if item.get('category', '').lower() == category)
            total_items = len(all_items)
            
            # If this category is over-represented, reduce its boost
            category_ratio = category_count / max(total_items, 1)
            
            if category_ratio > 0.4:  # More than 40% of one category
                return 0.8  # Reduce boost for variety
            elif category_ratio < 0.1:  # Underrepresented category
                return 1.2  # Increase boost for variety
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating variety boost: {e}")
            return 1.0
    
    def get_recommendations(self, context=None, count=8, user_id=None):
        """
        Get personalized food recommendations using Thompson Sampling
        
        Args:
            context: Context dictionary with meal_time, weather, region, etc.
            count: Number of recommendations to return
            user_id: User ID for personalization
            
        Returns:
            List of recommended food items with scores
        """
        try:
            # Get available foods from database
            available_foods = self.db.get_available_foods()
            
            if not available_foods:
                logger.warning("No available foods found")
                return []
            
            context_key = self._get_context_key(context)
            logger.info(f"Generating {count} recommendations for context: {context_key}")
            
            # Apply smart data-driven context boosts
            boosted_foods = self._apply_smart_context_boost(available_foods, context or {})
            
            # Calculate Thompson Sampling scores
            food_scores = {}
            
            for food_id, food_data in boosted_foods.items():
                food = food_data['food']
                boost = food_data['boost']
                
                # Get Thompson Sampling score
                ts_score = self._sample_beta_score(food_id, context_key)
                
                # Apply context boost
                final_score = ts_score * boost
                
                # Add user personalization if available
                if user_id:
                    user_history_boost = self._get_user_preference_boost(user_id, food)
                    final_score *= user_history_boost
                
                food_scores[food_id] = {
                    'food': food,
                    'score': final_score,
                    'ts_score': ts_score,
                    'context_boost': boost
                }
            
            # Sort by score and return top recommendations
            sorted_recommendations = sorted(
                food_scores.values(), 
                key=lambda x: x['score'], 
                reverse=True
            )
            
            recommendations = []
            for item in sorted_recommendations[:count]:
                recommendations.append({
                    'food_id': str(item['food']['_id']),
                    'name': item['food']['name'],
                    'category': item['food']['category'],
                    'price': item['food']['price'],
                    'image': item['food'].get('image', ''),
                    'score': item['score'],
                    'explanation': self._generate_explanation(item, context)
                })
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _get_user_preference_boost(self, user_id, food):
        """Calculate user preference boost based on order history"""
        try:
            user_orders = self.db.get_user_order_history(user_id, limit=20)
            
            if not user_orders:
                return 1.0  # No history, no boost
            
            # Count category preferences
            category_counts = defaultdict(int)
            for order in user_orders:
                for item in order.get('items', []):
                    # This would need to be enhanced to match food items properly
                    category_counts['general'] += 1
            
            # Simple boost based on category preference
            food_category = food.get('category', 'general')
            if category_counts.get(food_category, 0) > 0:
                return 1.2  # 20% boost for preferred categories
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating user preference boost: {e}")
            return 1.0
    
    def _generate_explanation(self, recommendation, context):
        """Generate human-readable explanation based on data factors"""
        try:
            food = recommendation['food']
            boost = recommendation.get('context_boost', 1.0)
            
            explanations = []
            
            # Data-driven explanations
            meal_time = context.get('meal_time') if context else None
            
            if meal_time == 'breakfast' and boost > 1.2:
                explanations.append("Perfect for breakfast")
            elif meal_time == 'lunch' and boost > 1.2:
                explanations.append("Great lunch choice")
            elif meal_time == 'dinner' and boost > 1.2:
                explanations.append("Satisfying dinner option")
            
            # Add popularity-based explanations
            if boost > 1.4:
                explanations.append("Highly rated by customers")
            elif boost > 1.2:
                explanations.append("Popular choice")
            
            # Add variety explanations
            category = food.get('category', '')
            if category.lower() in ['salad', 'vegan']:
                explanations.append("Fresh and healthy")
            elif category.lower() in ['seafood']:
                explanations.append("Premium quality")
            elif category.lower() in ['rice', 'noodle']:
                explanations.append("Filling and satisfying")
            
            if not explanations:
                explanations.append("Recommended based on your preferences")
            
            return "; ".join(explanations[:2])  # Limit to 2 explanations
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "Recommended for you"
    
    def get_statistics(self):
        """Get Thompson Sampling performance statistics"""
        try:
            total_items = len(self.item_stats)
            total_interactions = sum(
                sum(context_stats['total_interactions'] for context_stats in item_stats.values())
                for item_stats in self.item_stats.values()
            )
            
            return {
                'total_tracked_items': total_items,
                'total_interactions': total_interactions,
                'contexts_tracked': len(set(
                    context_key 
                    for item_stats in self.item_stats.values()
                    for context_key in item_stats.keys()
                ))
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total_tracked_items': 0, 'total_interactions': 0, 'contexts_tracked': 0}

    def reset_model_state(self):
        """
        Reset Thompson Sampling model state for fresh recommendations
        
        Returns:
            Dict with reset operation details
        """
        try:
            # Reset internal state tracking
            original_count = len(self.item_stats)
            
            # Reset item statistics
            self.item_stats = {}
            
            # Reset any cached recommendation data
            if hasattr(self, 'cached_recommendations'):
                self.cached_recommendations = {}
            
            # Reset performance tracking
            if hasattr(self, 'performance_history'):
                self.performance_history = []
            
            logger.info(f"Thompson Sampling model state reset - cleared {original_count} item statistics")
            
            return {
                'model_type': 'thompson_sampling',
                'items_cleared': original_count,
                'cache_cleared': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error resetting Thompson Sampling state: {e}")
            return {'error': str(e)}

# Singleton instance
thompson_sampler = None

def get_thompson_sampler():
    """Get singleton Thompson Sampling instance"""
    global thompson_sampler
    if thompson_sampler is None:
        thompson_sampler = ThompsonSampling()
    return thompson_sampler