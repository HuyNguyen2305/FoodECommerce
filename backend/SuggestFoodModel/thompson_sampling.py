# Thompson Sampling Algorithm for Food Recommendations
import numpy as np
from collections import defaultdict
import json
import logging
import random
from datetime import datetime
from database import get_food_database

logger = logging.getLogger(__name__)

class ThompsonSampling:
    """
    Thompson Sampling implementation for food delivery recommendations
    Uses Beta distribution to balance exploration vs exploitation for food recommendations
    """
    
    def __init__(self, alpha_prior=1.0, beta_prior=1.0, enable_persistence=True, exploration_mode='deterministic'):
        """
        Initialize Thompson Sampling with Beta distribution priors
        
        Args:
            alpha_prior: Prior successes (positive interactions)
            beta_prior: Prior failures (negative interactions)
            enable_persistence: Enable MongoDB persistence for learning
            exploration_mode: 'deterministic' (stable, uses mean) or 'stochastic' (random sampling)
        """
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.enable_persistence = enable_persistence
        self.exploration_mode = exploration_mode
        
        # Item statistics: {food_id: {context: {successes, failures}}}
        self.item_stats = defaultdict(lambda: defaultdict(lambda: {
            'successes': alpha_prior, 
            'failures': beta_prior,
            'total_interactions': 0,
            'last_updated': datetime.now()
        }))
        
        # Track pending saves for batch operations
        self.pending_saves = set()  # Set of (food_id, context_key) tuples
        self.last_save_time = datetime.now()
        
        # Context weights for food patterns
        self.context_weights = {
            'meal_time': 0.4,    # Strong influence (breakfast items in morning)
            'weather': 0.3,      # Medium influence (soup on rainy days)
            'user_history': 0.2, # User preferences
            'popularity': 0.1    # Trending items
        }
        
        self.db = get_food_database()
        
        # Load existing learned statistics from MongoDB
        if self.enable_persistence:
            self._load_stats_from_db()
        
        logger.info(f"Thompson Sampling initialized (mode={exploration_mode}, persistence={'ON' if enable_persistence else 'OFF'})")
    
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
            
            # Mark for persistence
            if self.enable_persistence:
                self.pending_saves.add((food_id, context_key))
                # Auto-save if we have many pending updates (batch efficiency)
                if len(self.pending_saves) >= 2:
                    self._batch_save_stats()
            
            logger.info(f"Updated {food_id} in context {context_key}: reward={reward_value}, type={interaction_type}")
            
        except Exception as e:
            logger.error(f"Error updating reward: {e}")
    
    def _sample_beta_score(self, food_id, context_key, mode=None):
        """
        Get score from Beta distribution (deterministic mean or stochastic sample)
        
        Args:
            food_id: Food item ID
            context_key: Context identifier
            mode: Override exploration mode ('deterministic' or 'stochastic')
        """
        try:
            stats = self.item_stats[food_id][context_key]
            alpha = stats['successes']
            beta = stats['failures']
            
            # Use specified mode or default to instance mode
            use_mode = mode or self.exploration_mode
            
            if use_mode == 'deterministic':
                # Use expected value (mean) of Beta distribution: alpha / (alpha + beta)
                # This gives stable, consistent recommendations
                score = alpha / (alpha + beta)
            else:
                # Stochastic mode: random sampling from Beta distribution
                # This provides exploration/exploitation tradeoff
                score = np.random.beta(alpha, beta)
            
            return score
        except Exception as e:
            logger.error(f"Error calculating beta score: {e}")
            # Fallback to prior mean
            return self.alpha_prior / (self.alpha_prior + self.beta_prior)
    
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
            
            # Get user's order history for content-based similarity
            user_ordered_items = []
            if user_id:
                # Use same extended history for content similarity
                user_orders = self.db.get_user_order_history(user_id, limit=100)
                for order in user_orders:
                    for item in order.get('items', []):
                        user_ordered_items.append(item)
            
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
                user_history_boost = 1.0
                user_order_count = 0
                if user_id:
                    user_history_boost, user_order_count = self._get_user_preference_boost(user_id, food)
                    final_score *= user_history_boost
                
                # Add small content-based similarity boost (0.0-0.3 range)
                content_boost = 0.0
                if user_ordered_items:
                    content_boost = self._get_content_similarity_boost(food, user_ordered_items)
                    final_score += content_boost  # ADDITIVE (not multiplicative)
                
                # Get GLOBAL order count (across all users, not just this user)
                global_stats = self.db.get_interaction_stats(food_id)
                global_order_count = global_stats.get('orders', 0)
                
                # Log scoring details for debugging
                food_name = food.get('name', 'Unknown')
                logger.info(f"[SCORE] {food_name}: global_orders={global_order_count}, ts={ts_score:.3f}, context={boost:.2f}x, user={user_history_boost:.2f}x, content=+{content_boost:.3f} → FINAL={final_score:.3f}")
                
                food_scores[food_id] = {
                    'food': food,
                    'score': final_score,
                    'ts_score': ts_score,
                    'context_boost': boost,
                    'user_boost': user_history_boost,
                    'order_count': user_order_count,
                    'global_order_count': global_order_count,  # Add global order count
                    'content_boost': content_boost,
                    'random_tiebreaker': random.random()  # Random value for fair tiebreaking
                }
            
            # Sort recommendations based on whether user is logged in
            if user_id:
                # LOGGED IN: Prioritize user's personal order history
                # Sort by USER ORDER COUNT first, then calculated score
                sorted_recommendations = sorted(
                    food_scores.values(), 
                    key=lambda x: (x['order_count'], x['score'], x['random_tiebreaker']), 
                    reverse=True
                )
                logger.info(f"[SORT] Personalized sorting by user order count for user {user_id}")
            else:
                # NEUTRAL USER: Prioritize global popularity with variety
                # Sort by GLOBAL ORDER COUNT, then random (for variety on each reload)
                sorted_recommendations = sorted(
                    food_scores.values(), 
                    key=lambda x: (x['global_order_count'], x['random_tiebreaker']), 
                    reverse=True
                )
                logger.info(f"[SORT] Non-personalized sorting by global popularity with randomization")
            
            # Log top recommendations for debugging
            logger.info(f"[TOP RECS] Top {min(count, len(sorted_recommendations))} recommendations:")
            for i, item in enumerate(sorted_recommendations[:count], 1):
                logger.info(f"  {i}. {item['food']['name']}: user_orders={item['order_count']}, score={item['score']:.3f}, global_orders={item['global_order_count']}")
            
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
        """Calculate user preference boost based on order history and name similarity
        Returns: (boost_multiplier, order_count)
        """
        try:
            # Get MORE order history to capture frequently ordered items (not just recent)
            user_orders = self.db.get_user_order_history(user_id, limit=100)
            
            logger.info(f"[USER BOOST] Checking user {user_id}: found {len(user_orders)} orders")
            
            if not user_orders:
                logger.warning(f"[USER BOOST] No order history found for user {user_id}")
                return 1.0, 0  # No history, no boost, 0 orders
            
            # Extract ordered food items and track order frequency
            ordered_names = []
            name_order_count = defaultdict(int)
            category_counts = defaultdict(int)
            
            for order in user_orders:
                for item in order.get('items', []):
                    item_name = item.get('name', '').lower()
                    item_category = item.get('category', '').lower()
                    item_quantity = item.get('quantity', 1)  # Get the quantity
                    
                    if item_name:
                        ordered_names.append(item_name)
                        name_order_count[item_name] += item_quantity  # Count total quantity, not just 1
                    if item_category:
                        category_counts[item_category] += item_quantity  # Also count category by quantity
            
            food_name = food.get('name', '').lower()
            food_category = food.get('category', '').lower()
            
            logger.info(f"[USER BOOST] Order counts: {dict(name_order_count)}")
            logger.info(f"[USER BOOST] Checking '{food_name}': order_count={name_order_count.get(food_name, 0)}")
            
            # 1. EXACT MATCH BOOST - Dishes user has ordered before get HUGE boost
            # Based on TOTAL order count (not just recent)
            exact_match_count = name_order_count.get(food_name, 0)
            if exact_match_count > 0:
                # Give massive boost based on order frequency
                boost = 1.0
                if exact_match_count >= 10:
                    boost = 50.0  # Ordered 10+ times = ABSOLUTE FAVORITE
                elif exact_match_count >= 7:
                    boost = 40.0  # Ordered 7+ times = SUPER FAVORITE
                elif exact_match_count >= 5:
                    boost = 30.0  # Ordered 5+ times = TOP PRIORITY
                elif exact_match_count >= 3:
                    boost = 20.0  # Ordered 3+ times = VERY HIGH PRIORITY
                elif exact_match_count >= 2:
                    boost = 12.0  # Ordered 2+ times = HIGH PRIORITY
                else:
                    boost = 5.0  # Ordered once = STRONG PRIORITY
                
                logger.info(f"[USER BOOST] '{food_name}' ordered {exact_match_count}x → BOOST: {boost}x")
                return boost, exact_match_count
            
            # 2. NAME SIMILARITY BOOST - Similar dishes get moderate boost
            boost = 1.0
            name_similarity_boost = self._calculate_name_similarity(food_name, ordered_names)
            boost *= name_similarity_boost
            
            # 3. CATEGORY PREFERENCE BOOST
            if category_counts.get(food_category, 0) > 0:
                category_frequency = category_counts[food_category]
                if category_frequency >= 5:
                    boost *= 1.4
                elif category_frequency >= 3:
                    boost *= 1.2
                elif category_frequency >= 1:
                    boost *= 1.1
            
            return min(boost, 2.0), 0  # Cap similarity+category boost at 2x, no exact orders
            
        except Exception as e:
            logger.error(f"Error calculating user preference boost: {e}")
            return 1.0, 0
    
    def _calculate_name_similarity(self, food_name, ordered_names):
        """Calculate similarity between food name and previously ordered dish names"""
        try:
            if not ordered_names:
                return 1.0
            
            # Extract key words from food name (ignore common words)
            common_words = {'with', 'and', 'or', 'the', 'in', 'on', 'special', 'deluxe', 'premium'}
            food_words = set(word for word in food_name.split() if word not in common_words and len(word) > 2)
            
            if not food_words:
                return 1.0
            
            # Check for word matches in ordered dish names
            max_similarity = 0
            for ordered_name in ordered_names:
                ordered_words = set(word for word in ordered_name.split() if word not in common_words and len(word) > 2)
                
                if not ordered_words:
                    continue
                
                # Calculate Jaccard similarity (intersection / union)
                intersection = food_words & ordered_words
                union = food_words | ordered_words
                
                if union:
                    similarity = len(intersection) / len(union)
                    max_similarity = max(max_similarity, similarity)
            
            # Convert similarity to boost factor
            if max_similarity > 0.5:  # Very similar (50%+ word overlap)
                return 1.5  # Strong boost
            elif max_similarity > 0.3:  # Somewhat similar (30%+ overlap)
                return 1.3
            elif max_similarity > 0.1:  # Slight similarity (10%+ overlap)
                return 1.1
            else:
                return 1.0  # No similarity
                
        except Exception as e:
            logger.error(f"Error calculating name similarity: {e}")
            return 1.0
    
    def _get_content_similarity_boost(self, food, user_ordered_items):
        """
        Calculate small content-based similarity boost based on ingredient overlap
        Returns: 0.0 - 0.3 boost (additive, not multiplicative)
        """
        try:
            if not user_ordered_items:
                return 0.0
            
            food_name = food.get('name', '').lower()
            food_description = food.get('description', '').lower()
            food_ingredients = food.get('ingredients', '').lower()
            
            # Combine all text for this food
            food_text = f"{food_name} {food_description} {food_ingredients}"
            food_words = set(word for word in food_text.split() if len(word) > 3)
            
            if not food_words:
                return 0.0
            
            # Extract words from ordered items
            ordered_words = set()
            for item in user_ordered_items:
                item_text = f"{item.get('name', '')} {item.get('description', '')}".lower()
                words = set(word for word in item_text.split() if len(word) > 3)
                ordered_words.update(words)
            
            if not ordered_words:
                return 0.0
            
            # Calculate Jaccard similarity (intersection / union)
            intersection = food_words & ordered_words
            union = food_words | ordered_words
            
            if not union:
                return 0.0
            
            similarity = len(intersection) / len(union)
            
            # Convert to small boost (0.0 - 0.3 range)
            # This is ADDITIVE to final score, not multiplicative
            if similarity > 0.4:    # Very similar ingredients
                return 0.3
            elif similarity > 0.3:  # Quite similar
                return 0.2
            elif similarity > 0.2:  # Somewhat similar
                return 0.15
            elif similarity > 0.1:  # Slightly similar
                return 0.1
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating content similarity boost: {e}")
            return 0.0
    
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
    
    def _load_stats_from_db(self):
        """
        Load existing Thompson Sampling statistics from MongoDB
        Runs on initialization to restore learned patterns
        """
        try:
            collection = self.db.db.thompson_sampling_stats
            
            # Load all existing statistics
            stats_docs = collection.find({})
            loaded_count = 0
            
            for doc in stats_docs:
                food_id = doc['food_id']
                context_key = doc['context_key']
                
                # Restore statistics to memory
                self.item_stats[food_id][context_key] = {
                    'successes': doc.get('successes', self.alpha_prior),
                    'failures': doc.get('failures', self.beta_prior),
                    'total_interactions': doc.get('total_interactions', 0),
                    'last_updated': doc.get('last_updated', datetime.now())
                }
                loaded_count += 1
            
            logger.info(f"[LEARNING] Loaded {loaded_count} learned statistics from MongoDB")
            
        except Exception as e:
            logger.warning(f"Could not load stats from DB (first run?): {e}")
    
    def _save_stats_to_db(self, food_id, context_key):
        """
        Save specific Thompson Sampling statistics to MongoDB
        
        Args:
            food_id: Food item ID
            context_key: Context key (e.g., 'meal_time:breakfast')
        """
        try:
            collection = self.db.db.thompson_sampling_stats
            stats = self.item_stats[food_id][context_key]
            
            # Upsert statistics document
            collection.update_one(
                {'food_id': food_id, 'context_key': context_key},
                {'$set': {
                    'successes': float(stats['successes']),
                    'failures': float(stats['failures']),
                    'total_interactions': int(stats['total_interactions']),
                    'last_updated': stats['last_updated']
                }},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error saving stats to DB: {e}")
    
    def _batch_save_stats(self):
        """
        Efficiently save all pending statistics to MongoDB in batch
        """
        try:
            if not self.pending_saves:
                return
            
            collection = self.db.db.thompson_sampling_stats
            
            # Use bulk_write with proper UpdateOne operations
            from pymongo import UpdateOne
            
            operations = []
            for food_id, context_key in self.pending_saves:
                stats = self.item_stats[food_id][context_key]
                
                operations.append(
                    UpdateOne(
                        {'food_id': food_id, 'context_key': context_key},
                        {'$set': {
                            'successes': float(stats['successes']),
                            'failures': float(stats['failures']),
                            'total_interactions': int(stats['total_interactions']),
                            'last_updated': stats['last_updated']
                        }},
                        upsert=True
                    )
                )
            
            # Execute batch write
            if operations:
                result = collection.bulk_write(operations)
                logger.info(f"[PERSIST] Saved {len(operations)} statistics to MongoDB")
            
            # Clear pending saves
            self.pending_saves.clear()
            self.last_save_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error batch saving stats: {e}")
    
    def sync_to_database(self):
        """
        Force synchronization of all learned statistics to database
        Call this periodically or before shutdown
        
        Returns:
            Dict with sync operation details
        """
        try:
            start_time = datetime.now()
            
            # Save any pending updates
            if self.pending_saves:
                self._batch_save_stats()
            
            # Count total stats in memory
            total_stats = sum(
                len(contexts) 
                for contexts in self.item_stats.values()
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[SYNC] Synced {total_stats} statistics to MongoDB in {duration:.2f}s")
            
            return {
                'success': True,
                'stats_synced': total_stats,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing to database: {e}")
            return {'success': False, 'error': str(e)}

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