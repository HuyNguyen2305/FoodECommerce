# Food Interaction Tracking System
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import json
from database import get_food_database
from thompson_sampling import get_thompson_sampler

logger = logging.getLogger(__name__)

class InteractionTracker:
    """
    Tracks and processes user interactions with food recommendations
    Handles clicks, views, orders, ratings, and other engagement metrics
    """
    
    def __init__(self):
        """Initialize interaction tracker for Vietnamese food delivery"""
        
        # Interaction types and their reward values
        self.interaction_rewards = {
            'view': 0.1,        # Low positive signal
            'click': 0.5,       # Medium positive signal  
            'add_to_cart': 0.7, # High positive signal
            'order': 1.0,       # Maximum positive signal
            'rating_1': 0.0,    # Negative feedback
            'rating_2': 0.2,    # Poor rating
            'rating_3': 0.5,    # Neutral rating
            'rating_4': 0.8,    # Good rating
            'rating_5': 1.0,    # Excellent rating
            'remove_from_cart': -0.3,  # Negative signal
            'skip': -0.1        # Mild negative signal
        }
        
        # Session tracking for analyzing user behavior patterns
        self.active_sessions = {}
        self.session_timeout = timedelta(hours=2)
        
        self.db = get_food_database()
        self.thompson_sampler = get_thompson_sampler()
        
        logger.info("Interaction Tracker initialized")
    
    def track_recommendation_view(self, user_id, food_id, context=None, session_id=None, algorithm='default'):
        """Track when a user views a recommended food item"""
        try:
            interaction_data = {
                'user_id': user_id,
                'food_id': food_id,
                'action': 'view',
                'context': context or {},
                'session_id': session_id,
                'timestamp': datetime.now(),
                'reward_value': self.interaction_rewards['view']
            }
            
            # Save to database
            self.db.save_interaction(interaction_data)
            
            # Update Thompson Sampling
            self.thompson_sampler.update_reward(
                food_id=food_id,
                context=context,
                reward_value=self.interaction_rewards['view'],
                interaction_type='view'
            )
            
            # Update session tracking
            self._update_session(user_id, session_id, 'view', food_id)
            
            logger.info(f"Tracked view: user={user_id}, food={food_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking recommendation view: {e}")
            return False
    
    def track_recommendation_click(self, user_id, food_id, context=None, session_id=None, click_position=None):
        """Track when a user clicks on a recommended food item"""
        try:
            # Calculate position-based reward (higher reward for top positions)
            position_bonus = 0
            if click_position is not None:
                position_bonus = max(0, (8 - click_position) * 0.05)  # Bonus for top positions
            
            base_reward = self.interaction_rewards['click']
            final_reward = min(base_reward + position_bonus, 1.0)
            
            interaction_data = {
                'user_id': user_id,
                'food_id': food_id,
                'action': 'click',
                'context': context or {},
                'session_id': session_id,
                'click_position': click_position,
                'timestamp': datetime.now(),
                'reward_value': final_reward
            }
            
            # Save to database
            self.db.save_interaction(interaction_data)
            
            # Update Thompson Sampling with enhanced reward
            self.thompson_sampler.update_reward(
                food_id=food_id,
                context=context,
                reward_value=final_reward,
                interaction_type='click'
            )
            
            # Update session tracking
            self._update_session(user_id, session_id, 'click', food_id)
            
            logger.info(f"Tracked click: user={user_id}, food={food_id}, position={click_position}, reward={final_reward}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking recommendation click: {e}")
            return False
    
    def track_order(self, user_id, food_items, order_value, context=None, session_id=None):
        """Track when a user places an order with recommended items"""
        try:
            tracked_items = []
            
            for item in food_items:
                food_id = item.get('food_id') or item.get('foodId')
                quantity = item.get('quantity', 1)
                
                if not food_id:
                    continue
                
                # Calculate reward based on order value and quantity
                base_reward = self.interaction_rewards['order']
                quantity_bonus = min(quantity * 0.1, 0.3)  # Bonus for multiple quantities
                value_bonus = min(order_value / 500000, 0.2)  # Bonus for high-value orders (VND)
                
                final_reward = min(base_reward + quantity_bonus + value_bonus, 1.0)
                
                interaction_data = {
                    'user_id': user_id,
                    'food_id': food_id,
                    'action': 'order',
                    'context': context or {},
                    'session_id': session_id,
                    'quantity': quantity,
                    'order_value': order_value,
                    'timestamp': datetime.now(),
                    'reward_value': final_reward
                }
                
                # Save to database
                self.db.save_interaction(interaction_data)
                
                # Update Thompson Sampling
                self.thompson_sampler.update_reward(
                    food_id=food_id,
                    context=context,
                    reward_value=final_reward,
                    interaction_type='order'
                )
                
                tracked_items.append(food_id)
            
            # Update session tracking
            self._update_session(user_id, session_id, 'order', tracked_items)
            
            logger.info(f"Tracked order: user={user_id}, items={len(tracked_items)}, value={order_value}")
            return len(tracked_items) > 0
            
        except Exception as e:
            logger.error(f"Error tracking order: {e}")
            return False
    
    def track_rating(self, user_id, food_id, rating, context=None, session_id=None, review_text=None):
        """Track when a user rates a food item"""
        try:
            if not (1 <= rating <= 5):
                logger.warning(f"Invalid rating value: {rating}")
                return False
            
            reward_key = f'rating_{rating}'
            reward_value = self.interaction_rewards.get(reward_key, 0.5)
            
            interaction_data = {
                'user_id': user_id,
                'food_id': food_id,
                'action': 'rating',
                'rating': rating,
                'context': context or {},
                'session_id': session_id,
                'review_text': review_text,
                'timestamp': datetime.now(),
                'reward_value': reward_value
            }
            
            # Save to database
            self.db.save_interaction(interaction_data)
            
            # Update Thompson Sampling
            self.thompson_sampler.update_reward(
                food_id=food_id,
                context=context,
                reward_value=reward_value,
                interaction_type='rating'
            )
            
            # Update session tracking
            self._update_session(user_id, session_id, 'rating', food_id)
            
            logger.info(f"Tracked rating: user={user_id}, food={food_id}, rating={rating}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking rating: {e}")
            return False
    
    def track_negative_interaction(self, user_id, food_id, action, context=None, session_id=None):
        """Track negative interactions (skip, remove from cart, etc.)"""
        try:
            if action not in ['skip', 'remove_from_cart']:
                logger.warning(f"Unknown negative action: {action}")
                return False
            
            reward_value = self.interaction_rewards.get(action, -0.1)
            
            interaction_data = {
                'user_id': user_id,
                'food_id': food_id,
                'action': action,
                'context': context or {},
                'session_id': session_id,
                'timestamp': datetime.now(),
                'reward_value': reward_value
            }
            
            # Save to database
            self.db.save_interaction(interaction_data)
            
            # Update Thompson Sampling with negative reward
            self.thompson_sampler.update_reward(
                food_id=food_id,
                context=context,
                reward_value=abs(reward_value),  # Convert to positive for beta distribution
                interaction_type='negative'
            )
            
            logger.info(f"Tracked negative interaction: user={user_id}, food={food_id}, action={action}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking negative interaction: {e}")
            return False
    
    def _update_session(self, user_id, session_id, action, food_data):
        """Update user session tracking for behavior analysis"""
        try:
            if not session_id:
                return
            
            session_key = f"{user_id}_{session_id}"
            current_time = datetime.now()
            
            # Initialize or update session
            if session_key not in self.active_sessions:
                self.active_sessions[session_key] = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'start_time': current_time,
                    'last_activity': current_time,
                    'actions': [],
                    'viewed_foods': set(),
                    'clicked_foods': set(),
                    'ordered_foods': set()
                }
            
            session = self.active_sessions[session_key]
            session['last_activity'] = current_time
            
            # Track action
            session['actions'].append({
                'action': action,
                'food_data': food_data,
                'timestamp': current_time
            })
            
            # Update food tracking sets
            if isinstance(food_data, str):  # Single food ID
                if action == 'view':
                    session['viewed_foods'].add(food_data)
                elif action == 'click':
                    session['clicked_foods'].add(food_data)
                elif action == 'order':
                    session['ordered_foods'].add(food_data)
            elif isinstance(food_data, list):  # Multiple food IDs
                if action == 'order':
                    session['ordered_foods'].update(food_data)
            
            # Clean up old sessions
            self._cleanup_old_sessions()
            
        except Exception as e:
            logger.error(f"Error updating session: {e}")
    
    def _cleanup_old_sessions(self):
        """Remove old inactive sessions"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_key, session in self.active_sessions.items():
                if current_time - session['last_activity'] > self.session_timeout:
                    expired_sessions.append(session_key)
            
            for session_key in expired_sessions:
                del self.active_sessions[session_key]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    def get_user_session_stats(self, user_id, session_id=None):
        """Get statistics for a user's current or recent session"""
        try:
            if session_id:
                session_key = f"{user_id}_{session_id}"
                if session_key in self.active_sessions:
                    session = self.active_sessions[session_key]
                    return {
                        'session_duration': (session['last_activity'] - session['start_time']).total_seconds(),
                        'total_actions': len(session['actions']),
                        'viewed_count': len(session['viewed_foods']),
                        'clicked_count': len(session['clicked_foods']),
                        'ordered_count': len(session['ordered_foods']),
                        'engagement_rate': len(session['clicked_foods']) / max(len(session['viewed_foods']), 1),
                        'conversion_rate': len(session['ordered_foods']) / max(len(session['clicked_foods']), 1)
                    }
            
            return {'error': 'Session not found or expired'}
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {'error': str(e)}
    
    def get_recommendation_performance(self, time_period_hours=24):
        """Get overall recommendation system performance metrics"""
        try:
            since = datetime.now() - timedelta(hours=time_period_hours)
            
            # This would need to be implemented with proper database aggregation
            # For now, return sample metrics
            return {
                'period_hours': time_period_hours,
                'total_recommendations_served': 0,
                'total_clicks': 0,
                'total_orders': 0,
                'click_through_rate': 0.0,
                'conversion_rate': 0.0,
                'average_rating': 0.0,
                'top_performing_categories': []
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation performance: {e}")
            return {'error': str(e)}

    def reset_user_session(self, user_id, session_id=None):
        """
        Reset user session data to clear recent activity tracking
        
        Args:
            user_id: User ID to reset
            session_id: Specific session ID to reset, or None to reset all user sessions
            
        Returns:
            Dict with reset operation details
        """
        try:
            reset_count = 0
            reset_sessions = []
            
            if session_id:
                # Reset specific session
                session_key = f"{user_id}_{session_id}"
                if session_key in self.active_sessions:
                    session_data = self.active_sessions[session_key].copy()
                    del self.active_sessions[session_key]
                    reset_count = 1
                    reset_sessions.append({
                        'session_id': session_id,
                        'actions_cleared': len(session_data.get('actions', [])),
                        'viewed_foods_cleared': len(session_data.get('viewed_foods', set())),
                        'clicked_foods_cleared': len(session_data.get('clicked_foods', set())),
                        'ordered_foods_cleared': len(session_data.get('ordered_foods', set()))
                    })
            else:
                # Reset all sessions for user
                sessions_to_remove = []
                for session_key in self.active_sessions:
                    if session_key.startswith(f"{user_id}_"):
                        sessions_to_remove.append(session_key)
                
                for session_key in sessions_to_remove:
                    session_data = self.active_sessions[session_key].copy()
                    session_id_part = session_key.split('_', 1)[1]
                    del self.active_sessions[session_key]
                    reset_count += 1
                    reset_sessions.append({
                        'session_id': session_id_part,
                        'actions_cleared': len(session_data.get('actions', [])),
                        'viewed_foods_cleared': len(session_data.get('viewed_foods', set())),
                        'clicked_foods_cleared': len(session_data.get('clicked_foods', set())),
                        'ordered_foods_cleared': len(session_data.get('ordered_foods', set()))
                    })
            
            logger.info(f"Reset {reset_count} sessions for user {user_id}")
            
            return {
                'user_id': user_id,
                'sessions_reset': reset_count,
                'reset_details': reset_sessions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error resetting user session: {e}")
            return {'error': str(e)}

# Singleton instance
interaction_tracker = None

def get_interaction_tracker():
    """Get singleton interaction tracker instance"""
    global interaction_tracker
    if interaction_tracker is None:
        interaction_tracker = InteractionTracker()
    return interaction_tracker