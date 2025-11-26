# Food Database Connection for ML Recommendations
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FoodDatabase:
    def __init__(self):
        """Initialize connection to same MongoDB used by Node.js backend"""
        try:
            # Get connection details from environment variables
            mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
            db_name = os.getenv('DATABASE_NAME', 'food-delivery')
            
            self.client = MongoClient(mongodb_url)
            self.db = self.client[db_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {db_name}")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def get_available_foods(self):
        """Get all available food items for recommendations"""
        try:
            # Query without 'available' filter since your foods don't have that field
            foods = list(self.db.foods.find(
                {}, 
                {
                    '_id': 1, 
                    'name': 1, 
                    'category': 1, 
                    'price': 1, 
                    'image': 1,
                    'description': 1,
                    'ingredients': 1  # Include ingredients if present
                }
            ))
            
            # If ingredients field doesn't exist, use description as ingredients
            for food in foods:
                if 'ingredients' not in food or not food.get('ingredients'):
                    food['ingredients'] = food.get('description', '')
            
            logger.info(f"Retrieved {len(foods)} available foods")
            return foods
        except Exception as e:
            logger.error(f"Error fetching foods: {e}")
            return []
    
    def get_user_order_history(self, user_id, limit=50):
        """Get user's past orders for personalization"""
        try:
            orders = list(self.db.orders.find(
                {'userId': user_id},
                {'items': 1, 'createdAt': 1, 'amount': 1}
            ).sort('createdAt', -1).limit(limit))
            
            logger.info(f"Retrieved {len(orders)} orders for user {user_id}")
            return orders
        except Exception as e:
            logger.error(f"Error fetching user orders: {e}")
            return []
    
    def get_context_foods(self, context_type, context_value):
        """Get foods based on meal time, weather, or other context"""
        context_mappings = {
            'meal_time': {
                'breakfast': ['Breakfast', 'Drinks', 'Pastry', 'Salad'],
                'lunch': ['Rice', 'Noodle', 'Pasta', 'Salad', 'Sandwich'],
                'dinner': ['Rice', 'Pasta', 'Seafood', 'Grill', 'Pizza']
            },
            'weather': {
                'rainy': {'$regex': 'soup|hot|warm|comfort', '$options': 'i'},
                'hot': {'$regex': 'salad|cold|drink|ice|fresh|smoothie', '$options': 'i'},
                'cool': {'$regex': 'warm|grilled|roasted|baked', '$options': 'i'}
            }
        }
        
        try:
            if context_type == 'meal_time':
                categories = context_mappings[context_type].get(context_value, [])
                query = {'category': {'$in': categories}, 'available': True}
            elif context_type == 'weather':
                name_pattern = context_mappings[context_type].get(context_value, {})
                query = {'name': name_pattern, 'available': True}
            else:
                query = {'available': True}
            
            foods = list(self.db.foods.find(query))
            logger.info(f"Retrieved {len(foods)} foods for {context_type}:{context_value}")
            return foods
        except Exception as e:
            logger.error(f"Error fetching context foods: {e}")
            return []
    
    def save_interaction(self, interaction_data):
        """Save user interaction for ML learning"""
        try:
            interaction_data['timestamp'] = datetime.now()
            result = self.db.interactions.insert_one(interaction_data)
            logger.info(f"Saved interaction: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error saving interaction: {e}")
            return None
    
    def get_popular_foods(self, time_period_hours=24, limit=20):
        """Get trending/popular foods based on recent orders"""
        try:
            since = datetime.now() - timedelta(hours=time_period_hours)
            
            # Aggregate popular items from recent orders
            pipeline = [
                {'$match': {'createdAt': {'$gte': since}}},
                {'$unwind': '$items'},
                {'$group': {
                    '_id': '$items.foodId', 
                    'order_count': {'$sum': '$items.quantity'}
                }},
                {'$sort': {'order_count': -1}},
                {'$limit': limit}
            ]
            
            popular_ids = [item['_id'] for item in self.db.orders.aggregate(pipeline)]
            
            # Get full food details
            popular_foods = list(self.db.foods.find(
                {'_id': {'$in': popular_ids}, 'available': True}
            ))
            
            logger.info(f"Retrieved {len(popular_foods)} popular foods")
            return popular_foods
        except Exception as e:
            logger.error(f"Error fetching popular foods: {e}")
            return []
    
    def get_interaction_stats(self, food_id):
        """Get interaction statistics for a specific food item"""
        try:
            interactions = list(self.db.interactions.find({'food_id': food_id}))
            
            stats = {
                'views': len([i for i in interactions if i.get('action') == 'view']),
                'clicks': len([i for i in interactions if i.get('action') == 'click']),
                'orders': len([i for i in interactions if i.get('action') == 'order']),
                'ratings': [i.get('rating', 0) for i in interactions if i.get('rating')]
            }
            
            # Calculate success rate (clicks + orders / views)
            total_engagements = stats['clicks'] + stats['orders']
            stats['success_rate'] = total_engagements / max(stats['views'], 1)
            stats['avg_rating'] = sum(stats['ratings']) / max(len(stats['ratings']), 1)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting interaction stats: {e}")
            return {'views': 0, 'clicks': 0, 'orders': 0, 'success_rate': 0, 'avg_rating': 0}
    
    def close_connection(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")

# Singleton instance
food_db = None

def get_food_database():
    """Get singleton database instance"""
    global food_db
    if food_db is None:
        food_db = FoodDatabase()
    return food_db