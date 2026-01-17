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
            
            # Setup indexes for ML persistence
            self._setup_indexes()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _setup_indexes(self):
        """Create indexes for Thompson Sampling statistics collection"""
        try:
            collection = self.db.thompson_sampling_stats
            
            # Create unique compound index on (food_id, context_key)
            collection.create_index(
                [('food_id', 1), ('context_key', 1)],
                unique=True,
                name='food_context_unique'
            )
            
            # Create index on last_updated for query optimization
            collection.create_index('last_updated', name='last_updated_idx')
            
            logger.info("✅ Thompson Sampling indexes created/verified")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
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
            # Try multiple query formats to handle different user_id formats
            queries_to_try = [
                {'userId': user_id},              # String match
                {'userId': str(user_id)},         # Ensure string
            ]
            
            # If user_id looks like an ObjectId, try that too
            if len(user_id) == 24:
                try:
                    from bson import ObjectId
                    queries_to_try.append({'userId': ObjectId(user_id)})
                except:
                    pass
            
            orders = []
            for query in queries_to_try:
                orders = list(self.db.orders.find(
                    query,
                    {'items': 1, 'createdAt': 1, 'amount': 1, 'userId': 1}
                ).sort('createdAt', -1).limit(limit))
                
                if orders:
                    logger.info(f"✅ Retrieved {len(orders)} orders for user {user_id} using query: {query}")
                    break
            
            if not orders:
                logger.warning(f"⚠️ No orders found for user {user_id}. Tried queries: {queries_to_try}")
                # Debug: Show sample order to see the actual userId format
                sample = self.db.orders.find_one({}, {'userId': 1})
                if sample:
                    logger.info(f"📝 Sample order userId format: {sample.get('userId')} (type: {type(sample.get('userId'))})")
            
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
        """Get interaction statistics for a specific food item - bootstrapped from order history"""
        try:
            from bson import ObjectId
            
            # Try to convert food_id to ObjectId if it's a string
            try:
                if isinstance(food_id, str):
                    food_object_id = ObjectId(food_id)
                else:
                    food_object_id = food_id
            except:
                food_object_id = food_id
            
            # Bootstrap from actual order data instead of interactions collection
            # Count how many times this food has been ordered
            order_count = 0
            total_quantity = 0
            ratings = []
            
            # Aggregate orders containing this food item
            orders = list(self.db.orders.find({'items.foodId': food_object_id}))
            
            for order in orders:
                for item in order.get('items', []):
                    # Handle both ObjectId and string comparisons
                    item_food_id = item.get('foodId')
                    if str(item_food_id) == str(food_object_id):
                        order_count += 1
                        total_quantity += item.get('quantity', 1)
                        
                        # Extract rating if available
                        if 'rating' in item and item['rating'] > 0:
                            ratings.append(item['rating'])
            
            # Bootstrap estimates (since we don't have view/click data yet)
            # Assume view-to-order conversion rate of ~10-15% for popular items
            estimated_views = max(order_count * 8, 1)  # Rough estimate: 8 views per order
            estimated_clicks = max(order_count * 2, 1)  # Rough estimate: 2 clicks per order
            
            stats = {
                'views': estimated_views,
                'clicks': estimated_clicks,
                'orders': order_count,
                'total_quantity': total_quantity,
                'ratings': ratings
            }
            
            # Calculate success rate (orders / estimated views)
            stats['success_rate'] = order_count / max(estimated_views, 1)
            
            # Calculate average rating
            if ratings:
                stats['avg_rating'] = sum(ratings) / len(ratings)
            else:
                # Estimate rating based on order frequency (popular items likely rated well)
                if order_count >= 50:
                    stats['avg_rating'] = 4.3  # Very popular = good rating
                elif order_count >= 20:
                    stats['avg_rating'] = 4.0  # Popular = decent rating
                elif order_count >= 5:
                    stats['avg_rating'] = 3.8  # Some orders = okay rating
                else:
                    stats['avg_rating'] = 3.5  # Few orders = neutral
            
            logger.debug(f"Stats for food {food_id}: {order_count} orders, {stats['avg_rating']:.1f} rating")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting interaction stats for {food_id}: {e}")
            return {'views': 1, 'clicks': 0, 'orders': 0, 'success_rate': 0, 'avg_rating': 3.5}
    
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