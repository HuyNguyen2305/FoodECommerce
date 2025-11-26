# Content-Based Recommendation Routes
from flask import request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_content_based_routes(app, content_recommender, food_db, interaction_tracker):
    """Register content-based recommendation endpoints"""
    
    content_model_trained = {'trained': False}
    
    @app.route('/content-based/train', methods=['POST'])
    def train_content_model():
        """Train the content-based recommendation model"""
        try:
            logger.info("Training content-based recommendation model...")
            foods = food_db.get_available_foods()
            
            if not foods:
                return jsonify({'success': False, 'error': 'No food data available for training'}), 400
            
            content_recommender.fit_tfidf_model(foods)
            content_model_trained['trained'] = True
            
            return jsonify({
                'success': True,
                'message': f'Content-based model trained on {len(foods)} food items',
                'vocabulary_size': len(content_recommender.ingredient_vocabulary),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error training content model: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/content-based/similar/<food_id>', methods=['GET'])
    def get_similar_foods(food_id):
        """Get similar foods based on ingredients"""
        try:
            if not content_model_trained['trained']:
                return jsonify({'success': False, 'error': 'Model not trained. Call /content-based/train first.'}), 400
            
            count = min(int(request.args.get('count', 8)), 20)
            method = request.args.get('method', 'cosine')
            
            logger.info(f"Getting {method} similarity recommendations for food {food_id}")
            
            if method == 'jaccard':
                recommendations = content_recommender.get_jaccard_similarity_recommendations(food_id, count)
            else:
                recommendations = content_recommender.get_item_similarity_recommendations(food_id, count)
            
            if not recommendations:
                return jsonify({'success': False, 'error': f'No similar foods found for {food_id}'}), 404
            
            return jsonify({
                'success': True,
                'food_id': food_id,
                'method': method,
                'count': len(recommendations),
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting similar foods: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/content-based/cold-start', methods=['GET'])
    def get_cold_start_recommendations():
        """Get recommendations for new users based on time"""
        try:
            if not content_model_trained['trained']:
                return jsonify({'success': False, 'error': 'Model not trained. Call /content-based/train first.'}), 400
            
            count = min(int(request.args.get('count', 8)), 20)
            hour = request.args.get('hour', type=int)
            
            logger.info(f"Getting cold-start recommendations for hour {hour or 'current'}")
            recommendations = content_recommender.get_cold_start_recommendations(hour, count)
            
            return jsonify({
                'success': True,
                'strategy': 'cold-start',
                'hour': hour or datetime.now().hour,
                'count': len(recommendations),
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting cold-start recommendations: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/content-based/personalized', methods=['POST'])
    def get_personalized_recommendations():
        """Get personalized recommendations based on user preferences"""
        try:
            if not content_model_trained['trained']:
                return jsonify({'success': False, 'error': 'Model not trained. Call /content-based/train first.'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Request body required'}), 400
            
            user_id = data.get('user_id')
            user_food_data = data.get('user_food_data', {})
            count = min(data.get('count', 8), 20)
            
            if not user_id:
                return jsonify({'success': False, 'error': 'user_id required'}), 400
            
            logger.info(f"Personalized recommendation request for user {user_id}")
            recommendations = content_recommender.get_user_preference_recommendations(user_food_data, count)
            
            if recommendations:
                for rec in recommendations:
                    interaction_tracker.track_recommendation_view(
                        user_id=user_id,
                        food_id=str(rec.get('_id')),
                        algorithm='content-based-personalized',
                        context={'method': 'user_preferences'}
                    )
            
            return jsonify({
                'success': True,
                'strategy': 'personalized-preferences',
                'user_id': user_id,
                'count': len(recommendations),
                'recommendations': recommendations,
                'user_preferences_used': bool(user_food_data.get('orderedItems')),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in personalized recommendations: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/content-based/recommend', methods=['POST'])
    def get_unified_content_recommendations():
        """Unified content-based recommendation endpoint"""
        try:
            if not content_model_trained['trained']:
                return jsonify({'success': False, 'error': 'Model not trained. Call /content-based/train first.'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Request body required'}), 400
            
            user_id = data.get('user_id')
            target_food_id = data.get('food_id')
            user_food_data = data.get('user_food_data', {})
            count = min(data.get('count', 8), 20)
            
            logger.info(f"Unified content recommendation request for user {user_id}")
            
            # Strategy selection
            if user_food_data.get('preferences') and len(user_food_data.get('preferences', {})) > 3:
                logger.info(f"Using PERSONALIZED strategy - user has {len(user_food_data.get('preferences', {}))} preferences")
                recommendations = content_recommender.get_user_preference_recommendations(user_food_data, count)
                strategy = 'personalized-preferences'
                context = {'method': 'user_ingredient_preferences', 'preference_count': len(user_food_data.get('preferences', {}))}
            elif target_food_id:
                logger.info(f"Using item-similarity strategy for food {target_food_id}")
                recommendations = content_recommender.get_item_similarity_recommendations(target_food_id, count)
                strategy = 'item-similarity'
                context = {'target_food_id': target_food_id, 'method': 'cosine_similarity'}
            else:
                logger.info("Using cold-start strategy based on time-of-day")
                recommendations = content_recommender.get_cold_start_recommendations(None, count)
                strategy = 'cold-start'
                context = {'meal_time': 'auto-detected', 'method': 'time_filtering'}
            
            if user_id and recommendations:
                for rec in recommendations:
                    interaction_tracker.track_recommendation_view(
                        user_id=user_id,
                        food_id=str(rec.get('_id')),
                        algorithm=f'content-based-{strategy}',
                        context=context
                    )
            
            return jsonify({
                'success': True,
                'strategy': strategy,
                'user_id': user_id,
                'count': len(recommendations),
                'recommendations': recommendations,
                'context': context,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in unified content recommendations: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
