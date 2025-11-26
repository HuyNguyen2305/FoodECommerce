# Context Detection Utilities
from datetime import datetime

class SimpleContextDetector:
    """Simplified context detection for meal time recommendations"""
    
    def detect_meal_time(self, hour=None):
        """Detect meal time based on eating patterns"""
        if hour is None:
            hour = datetime.now().hour
        
        if 5 <= hour < 11:
            return 'breakfast'
        elif 11 <= hour < 16:
            return 'lunch'  
        elif 16 <= hour < 22:
            return 'dinner'
        else:
            return 'late_night'
    
    def get_meal_preferences(self, meal_time):
        """Get food category preferences by meal time"""
        preferences = {
            'breakfast': {
                'boost_categories': ['Noodle', 'Salad', 'Vegan'],
                'boost_keywords': ['light', 'fresh', 'energizing', 'healthy']
            },
            'lunch': {
                'boost_categories': ['Rice', 'Noodle', 'Salad', 'Vegan'],
                'boost_keywords': ['balanced', 'satisfying', 'nutritious', 'complete']
            },
            'dinner': {
                'boost_categories': ['Rice', 'Seafood', 'Noodle'],
                'boost_keywords': ['hearty', 'satisfying', 'protein-rich', 'filling']
            },
            'late_night': {
                'boost_categories': ['Noodle', 'Salad'],
                'boost_keywords': ['light', 'easy-digest', 'quick']
            }
        }
        return preferences.get(meal_time, preferences['lunch'])
    
    def build_context(self, request_data=None):
        """Build context for recommendations"""
        current_time = datetime.now()
        meal_time = self.detect_meal_time(current_time.hour)
        
        context = {
            'meal_time': meal_time,
            'hour': current_time.hour,
            'is_weekend': current_time.weekday() >= 5,
            'preferences': self.get_meal_preferences(meal_time)
        }
        
        if request_data:
            context.update({
                'user_id': request_data.get('user_id'),
                'session_id': request_data.get('session_id'),
                'user_preferences': request_data.get('preferences', {})
            })
        
        return context
