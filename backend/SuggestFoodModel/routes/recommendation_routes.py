# Core Recommendation Routes
from flask import request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_recommendation_routes(app, food_db, thompson_sampler, interaction_tracker, context_detector):
    """Register core recommendation endpoints"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'Food Recommendation System',
            'timestamp': datetime.now().isoformat()
        })

    @app.route('/recommend', methods=['POST'])
    def get_recommendations():
        """Get personalized food recommendations"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            count = min(data.get('count', 8), 20)
            session_id = data.get('session_id')
            
            if not user_id:
                return jsonify({'error': 'user_id is required'}), 400
            
            context = context_detector.build_context(data)
            logger.info(f"Getting {count} recommendations for user {user_id}, meal_time: {context['meal_time']}")
            
            recommendations = thompson_sampler.get_recommendations(
                context=context,
                count=count,
                user_id=user_id
            )
            
            for i, rec in enumerate(recommendations):
                interaction_tracker.track_recommendation_view(
                    user_id=user_id,
                    food_id=rec['food_id'],
                    context=context,
                    session_id=session_id
                )
                rec['position'] = i + 1
            
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'context': {
                    'meal_time': context['meal_time'],
                    'hour': context['hour'],
                    'is_weekend': context['is_weekend']
                },
                'count': len(recommendations),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/stats', methods=['GET'])
    def get_stats():
        """Get recommendation system statistics"""
        try:
            ts_stats = thompson_sampler.get_statistics()
            available_foods = food_db.get_available_foods()
            
            stats = {
                'system_status': 'active',
                'available_foods_count': len(available_foods),
                'thompson_sampling': ts_stats,
                'current_context': context_detector.build_context(),
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/foods', methods=['GET'])
    def get_available_foods():
        """Get all available foods"""
        try:
            foods = food_db.get_available_foods()
            
            categorized_foods = {}
            for food in foods:
                category = food.get('category', 'Other')
                if category not in categorized_foods:
                    categorized_foods[category] = []
                categorized_foods[category].append({
                    'id': str(food['_id']),
                    'name': food['name'],
                    'price': food['price']
                })
            
            return jsonify({
                'success': True,
                'categories': categorized_foods,
                'total_count': len(foods),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting foods: {e}")
            return jsonify({'error': str(e)}), 500
