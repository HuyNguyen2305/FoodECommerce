# Flask API Server for Food Recommendations
from flask import Flask
from flask_cors import CORS
import os
import logging

# Import recommendation system components
from database import get_food_database
from thompson_sampling import get_thompson_sampler
from interaction_tracker import get_interaction_tracker
from content_based_recommender import get_content_recommender
from utils.context_utils import SimpleContextDetector

# Import route modules
from routes.recommendation_routes import register_recommendation_routes
from routes.tracking_routes import register_tracking_routes
from routes.content_based_routes import register_content_based_routes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize recommendation system components
food_db = get_food_database()
thompson_sampler = get_thompson_sampler()
interaction_tracker = get_interaction_tracker()
content_recommender = get_content_recommender()
context_detector = SimpleContextDetector()

# Register all routes
register_recommendation_routes(app, food_db, thompson_sampler, interaction_tracker, context_detector)
register_tracking_routes(app, interaction_tracker, context_detector)
register_content_based_routes(app, content_recommender, food_db, interaction_tracker)

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 8000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Food Recommendation API on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)
