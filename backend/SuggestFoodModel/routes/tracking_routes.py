# User Interaction Tracking Routes
from flask import request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_tracking_routes(app, interaction_tracker, context_detector):
    """Register user tracking endpoints"""
    
    @app.route('/track/click', methods=['POST'])
    def track_click():
        """Track when user clicks on a recommended food item"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            food_id = data.get('food_id')
            position = data.get('position')
            session_id = data.get('session_id')
            
            if not user_id or not food_id:
                return jsonify({'error': 'user_id and food_id are required'}), 400
            
            context = context_detector.build_context(data)
            
            success = interaction_tracker.track_recommendation_click(
                user_id=user_id,
                food_id=food_id,
                context=context,
                session_id=session_id,
                click_position=position
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Click tracked successfully',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to track click'}), 500
                
        except Exception as e:
            logger.error(f"Error tracking click: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/track/order', methods=['POST'])
    def track_order():
        """Track when user places an order"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            food_items = data.get('food_items', [])
            order_value = data.get('order_value', 0)
            session_id = data.get('session_id')
            
            if not user_id or not food_items:
                return jsonify({'error': 'user_id and food_items are required'}), 400
            
            context = context_detector.build_context(data)
            
            success = interaction_tracker.track_order(
                user_id=user_id,
                food_items=food_items,
                order_value=order_value,
                context=context,
                session_id=session_id
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Order tracked successfully for {len(food_items)} items',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to track order'}), 500
                
        except Exception as e:
            logger.error(f"Error tracking order: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/track/rating', methods=['POST'])
    def track_rating():
        """Track when user rates a food item"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            food_id = data.get('food_id')
            rating = data.get('rating')
            review_text = data.get('review_text')
            session_id = data.get('session_id')
            
            if not user_id or not food_id or rating is None:
                return jsonify({'error': 'user_id, food_id, and rating are required'}), 400
            
            if not (1 <= rating <= 5):
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            
            context = context_detector.build_context(data)
            
            success = interaction_tracker.track_rating(
                user_id=user_id,
                food_id=food_id,
                rating=rating,
                context=context,
                session_id=session_id,
                review_text=review_text
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Rating tracked successfully',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to track rating'}), 500
                
        except Exception as e:
            logger.error(f"Error tracking rating: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
