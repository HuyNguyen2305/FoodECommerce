"""
Content-Based Food Recommendation System
======================================

Implements sophisticated content-based filtering using:
1. Ingredient canonicalization and preprocessing
2. TF-IDF vectorization for feature weighting  
3. Cosine similarity for item-item recommendations
4. Jaccard index baseline for binary ingredient overlap
5. Cold-start handling with time-based meal category filtering

Strategy:
- Engaged users: Item-item similarity based on ingredient vectors
- New users: Domain knowledge filtering by time-of-day + popularity ranking
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Set, Optional, Any
from collections import Counter, defaultdict
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os

logger = logging.getLogger(__name__)

class IngredientProcessor:
    """
    Handles ingredient canonicalization, lemmatization, and entity resolution
    """
    
    def __init__(self):
        """Initialize ingredient processing with canonicalization rules"""
        
        # Lemmatization rules for common plurals
        self.plural_to_singular = {
            'tomatoes': 'tomato',
            'potatoes': 'potato', 
            'onions': 'onion',
            'carrots': 'carrot',
            'peppers': 'pepper',
            'mushrooms': 'mushroom',
            'beans': 'bean',
            'noodles': 'noodle',
            'vegetables': 'vegetable',
            'herbs': 'herb',
            'spices': 'spice',
            'eggs': 'egg',
            'apples': 'apple',
            'bananas': 'banana',
            'berries': 'berry',
            'croutons': 'crouton',
            'olives': 'olive',
            'anchovies': 'anchovy',
            'capers': 'caper',
            'greens': 'green',
            'leaves': 'leaf',
        }
        
        # Entity resolution rules - map variants to canonical forms
        self.entity_mappings = {
            # Chocolate variants
            'milk chocolate': 'chocolate',
            'dark chocolate': 'chocolate', 
            'white chocolate': 'chocolate',
            'cocoa powder': 'chocolate',
            
            # Protein variants (keep specific for salads)
            'chicken breast': 'chicken',
            'chicken thigh': 'chicken',
            'ground beef': 'beef',
            'beef steak': 'beef',
            'pork chop': 'pork',
            'egg yolk': 'egg_yolk',  # Keep separate from whole egg
            'egg white': 'egg_white',
            
            # Dairy variants (preserve cheese specificity)
            'whole milk': 'milk',
            'skim milk': 'milk',
            'heavy cream': 'cream',
            'sour cream': 'cream',
            'parmesan cheese': 'parmesan',
            'parmigiano reggiano': 'parmesan',
            'mozzarella cheese': 'mozzarella',
            'cheddar cheese': 'cheddar',
            'feta cheese': 'feta',
            'goat cheese': 'goat_cheese',
            
            # Oil variants (keep olive oil distinct for salads)
            'extra virgin olive oil': 'olive_oil',
            'vegetable oil': 'cooking_oil',
            'canola oil': 'cooking_oil',
            'coconut oil': 'coconut_oil',
            'sesame oil': 'sesame_oil',
            
            # Rice variants
            'brown rice': 'rice',
            'white rice': 'rice',
            'jasmine rice': 'rice',
            
            # Vegetable preparations
            'romaine lettuce': 'romaine',
            'iceberg lettuce': 'lettuce',
            'mixed greens': 'salad_greens',
            'green onion': 'scallion',
            'spring onion': 'scallion',
            'bell pepper': 'bell_pepper',
            'sweet pepper': 'bell_pepper',
            'black pepper': 'black_pepper',
            'red onion': 'red_onion',
            'yellow onion': 'onion',
            
            # Citrus
            'lemon juice': 'lemon',
            'lime juice': 'lime',
            'orange juice': 'orange',
        }
        
        # Common stop ingredients (too generic for meaningful similarity)
        # Reduced list - keep flavor-impacting ingredients like pepper
        self.stop_ingredients = {
            'water', 'salt', 'served with', 'fresh', 'hot', 'cold',
            'cooked', 'served', 'prepared', 'mixed', 'chopped', 'sliced',
            'diced', 'minced', 'garnished', 'topped', 'drizzled'
        }
        
        logger.info("Ingredient processor initialized with canonicalization rules")
    
    def canonicalize_ingredient(self, ingredient: str) -> str:
        """
        Canonicalize single ingredient through lemmatization and entity resolution
        
        Args:
            ingredient: Raw ingredient string
            
        Returns:
            Canonicalized ingredient string
        """
        # Clean and normalize
        ingredient = ingredient.lower().strip()
        ingredient = re.sub(r'[^\w\s]', '', ingredient)  # Remove punctuation
        ingredient = re.sub(r'\s+', ' ', ingredient)      # Normalize whitespace
        
        # Apply entity resolution first (handles multi-word mappings)
        if ingredient in self.entity_mappings:
            ingredient = self.entity_mappings[ingredient]
        
        # Apply lemmatization (singular forms)
        if ingredient in self.plural_to_singular:
            ingredient = self.plural_to_singular[ingredient]
        
        return ingredient
    
    def process_ingredient_list(self, ingredients_str: str, remove_stop_words: bool = True) -> List[str]:
        """
        Process comma-separated ingredient list into canonicalized tokens
        
        Args:
            ingredients_str: Comma-separated ingredient string
            remove_stop_words: Whether to filter out common stop ingredients
            
        Returns:
            List of canonicalized ingredients
        """
        if not ingredients_str:
            return []
        
        # Split by comma and canonicalize each ingredient
        ingredients = [
            self.canonicalize_ingredient(ing.strip()) 
            for ing in ingredients_str.split(',')
        ]
        
        # Remove empty strings and optionally stop words
        ingredients = [ing for ing in ingredients if ing]
        
        if remove_stop_words:
            ingredients = [ing for ing in ingredients if ing not in self.stop_ingredients]
        
        return ingredients

class ContentBasedRecommender:
    """
    Core content-based recommendation engine using TF-IDF and cosine similarity
    """
    
    def __init__(self):
        """Initialize content-based recommender"""
        self.ingredient_processor = IngredientProcessor()
        self.tfidf_vectorizer = None
        self.food_vectors = None
        self.food_data = []
        self.food_id_to_index = {}
        self.ingredient_vocabulary = set()
        
        # Meal category mappings for cold-start
        self.meal_categories = {
            'breakfast': ['breakfast', 'morning', 'brunch'],
            'lunch': ['lunch', 'midday', 'light meal'],
            'dinner': ['dinner', 'evening', 'main course'],
            'dessert': ['dessert', 'sweet', 'cake', 'ice cream'],
            'snack': ['snack', 'appetizer', 'finger food']
        }
        
        logger.info("Content-based recommender initialized")
    
    def build_food_corpus(self, foods_data: List[Dict]) -> List[str]:
        """
        Build text corpus from food ingredient lists for TF-IDF
        
        Args:
            foods_data: List of food dictionaries with ingredient data
            
        Returns:
            List of processed ingredient strings (one per food item)
        """
        corpus = []
        
        for food in foods_data:
            # Get ingredients from food data
            ingredients_raw = food.get('ingredients', '') or food.get('description', '')
            
            # Process ingredients into canonicalized tokens
            ingredients_processed = self.ingredient_processor.process_ingredient_list(ingredients_raw)
            
            # Join processed ingredients back into document string
            ingredient_document = ' '.join(ingredients_processed)
            corpus.append(ingredient_document)
            
            # Build vocabulary set
            self.ingredient_vocabulary.update(ingredients_processed)
        
        logger.info(f"Built corpus of {len(corpus)} food documents with {len(self.ingredient_vocabulary)} unique ingredients")
        return corpus
    
    def fit_tfidf_model(self, foods_data: List[Dict]):
        """
        Fit TF-IDF vectorizer on food ingredient corpus
        
        Args:
            foods_data: List of food dictionaries to train on
        """
        logger.info("Fitting TF-IDF model on food ingredients...")
        
        # Store food data and create index mapping
        self.food_data = foods_data
        self.food_id_to_index = {
            str(food.get('_id', i)): i 
            for i, food in enumerate(foods_data)
        }
        
        # Build ingredient corpus
        ingredient_corpus = self.build_food_corpus(foods_data)
        
        # Configure TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,        # Limit vocabulary size
            min_df=2,                 # Ingredient must appear in at least 2 documents
            max_df=0.8,               # Ignore ingredients in >80% of documents (too common)
            ngram_range=(1, 2),       # Use unigrams and bigrams
            stop_words=None,          # We handle stop words in preprocessing
            lowercase=True,
            token_pattern=r'\b\w+\b'  # Simple word tokenization
        )
        
        # Fit and transform ingredient corpus to TF-IDF vectors
        self.food_vectors = self.tfidf_vectorizer.fit_transform(ingredient_corpus)
        
        logger.info(f"TF-IDF model fitted: {self.food_vectors.shape[0]} foods, {self.food_vectors.shape[1]} features")
    
    def get_item_similarity_recommendations(self, food_id: str, top_n: int = 8) -> List[Dict]:
        """
        Get recommendations based on item-item similarity using cosine similarity
        
        Args:
            food_id: ID of the food item to find similar items for
            top_n: Number of recommendations to return
            
        Returns:
            List of similar food recommendations with similarity scores
        """
        if not self.tfidf_vectorizer or self.food_vectors is None:
            logger.error("TF-IDF model not fitted. Call fit_tfidf_model() first.")
            return []
        
        # Get index of target food item
        if food_id not in self.food_id_to_index:
            logger.warning(f"Food ID {food_id} not found in trained data")
            return []
        
        target_index = self.food_id_to_index[food_id]
        target_vector = self.food_vectors[target_index]
        
        # Calculate cosine similarity with all other items
        similarity_scores = cosine_similarity(target_vector, self.food_vectors).flatten()
        
        # Get top similar items (excluding self)
        similar_indices = np.argsort(similarity_scores)[::-1][1:top_n+1]  # Exclude self (index 0)
        
        # Build recommendations with similarity scores
        recommendations = []
        for idx in similar_indices:
            similarity_score = similarity_scores[idx]
            food_item = self.food_data[idx].copy()
            food_item['similarity_score'] = float(similarity_score)
            food_item['recommendation_reason'] = f"Similar ingredients (score: {similarity_score:.3f})"
            recommendations.append(food_item)
        
        logger.info(f"Generated {len(recommendations)} item-similarity recommendations for food {food_id}")
        return recommendations
    
    def get_jaccard_similarity_recommendations(self, food_id: str, top_n: int = 8) -> List[Dict]:
        """
        Baseline recommendation using Jaccard Index for binary ingredient overlap
        
        Args:
            food_id: ID of the food item to find similar items for  
            top_n: Number of recommendations to return
            
        Returns:
            List of similar food recommendations with Jaccard similarity scores
        """
        if food_id not in self.food_id_to_index:
            logger.warning(f"Food ID {food_id} not found in data")
            return []
        
        target_index = self.food_id_to_index[food_id]
        target_food = self.food_data[target_index]
        
        # Get target ingredients as set
        target_ingredients_raw = target_food.get('ingredients', '') or target_food.get('description', '')
        target_ingredients = set(self.ingredient_processor.process_ingredient_list(target_ingredients_raw))
        
        # Calculate Jaccard similarity with all other foods
        similarities = []
        for i, food in enumerate(self.food_data):
            if i == target_index:  # Skip self
                continue
            
            # Get food ingredients as set
            food_ingredients_raw = food.get('ingredients', '') or food.get('description', '')
            food_ingredients = set(self.ingredient_processor.process_ingredient_list(food_ingredients_raw))
            
            # Calculate Jaccard similarity
            intersection = len(target_ingredients & food_ingredients)
            union = len(target_ingredients | food_ingredients)
            jaccard_score = intersection / union if union > 0 else 0.0
            
            similarities.append((i, jaccard_score, food))
        
        # Sort by similarity and get top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similarities = similarities[:top_n]
        
        # Build recommendations
        recommendations = []
        for idx, jaccard_score, food_item in top_similarities:
            food_copy = food_item.copy()
            food_copy['similarity_score'] = float(jaccard_score)
            food_copy['recommendation_reason'] = f"Ingredient overlap (Jaccard: {jaccard_score:.3f})"
            recommendations.append(food_copy)
        
        logger.info(f"Generated {len(recommendations)} Jaccard similarity recommendations for food {food_id}")
        return recommendations
    
    def classify_meal_category(self, food_name: str, ingredients: str) -> str:
        """
        Simple rule-based meal category classification
        (In production, this would be a trained ML classifier)
        
        Args:
            food_name: Name of the food
            ingredients: Ingredient list string
            
        Returns:
            Predicted meal category
        """
        text = f"{food_name} {ingredients}".lower()
        
        # Breakfast indicators
        breakfast_keywords = ['egg', 'cereal', 'oatmeal', 'pancake', 'waffle', 'toast', 'yogurt', 'smoothie', 'bagel', 'muffin']
        if any(keyword in text for keyword in breakfast_keywords):
            return 'breakfast'
        
        # Dessert indicators  
        dessert_keywords = ['cake', 'cookie', 'ice cream', 'chocolate', 'candy', 'sweet', 'dessert', 'pie', 'tart']
        if any(keyword in text for keyword in dessert_keywords):
            return 'dessert'
        
        # Lunch indicators (lighter meals)
        lunch_keywords = ['salad', 'sandwich', 'wrap', 'soup', 'bowl']
        if any(keyword in text for keyword in lunch_keywords):
            return 'lunch'
        
        # Default to dinner for substantial dishes
        return 'dinner'
    
    def get_user_preference_recommendations(self, user_food_data: Dict, top_n: int = 8) -> List[Dict]:
        """
        Get personalized recommendations based PURELY on user's food preferences
        Focuses on ingredients the user actually loves (excluding salt/pepper/generic items)
        
        Args:
            user_food_data: User's food preference data from MongoDB
            top_n: Number of recommendations to return
            
        Returns:
            List of personalized food recommendations based on user taste
        """
        ordered_items = user_food_data.get('orderedItems', {})
        preferences = user_food_data.get('preferences', {})
        
        # Debug logging for ordered items
        logger.info(f"User has ordered {len(ordered_items)} different foods")
        if ordered_items:
            # Show heavily ordered items
            heavy_orders = {food_id: count for food_id, count in ordered_items.items() if count >= 4}
            if heavy_orders:
                logger.info(f"Heavily ordered items (4+ times): {heavy_orders}")
        
        if not preferences:
            # Fall back to cold-start if no user preference data
            logger.info("No user preferences found, falling back to cold-start recommendations")
            return self.get_cold_start_recommendations(None, top_n)
        
        # Filter out generic ingredients and focus on meaningful preferences
        filtered_preferences = {}
        for ingredient, count in preferences.items():
            # Skip generic/cooking method words
            if (ingredient not in self.stop_ingredients and 
                len(ingredient) > 2 and 
                not any(word in ingredient.lower() for word in ['with', 'and', 'or', 'the', 'is', 'are'])):
                filtered_preferences[ingredient] = count
        
        if not filtered_preferences:
            logger.info("No meaningful user preferences after filtering, using cold-start")
            return self.get_cold_start_recommendations(None, top_n)
        
        # Get user's top preferred ingredients (focus on most loved ingredients)
        top_preferences = sorted(filtered_preferences.items(), key=lambda x: x[1], reverse=True)[:10]
        preferred_ingredients = set([ingredient for ingredient, _ in top_preferences])
        
        logger.info(f"User's top ingredients: {[f'{ing}({count})' for ing, count in top_preferences[:5]]}")
        
        # Score foods based PURELY on user preferences
        recommendations = []
        for food in self.food_data:
            food_id = str(food.get('_id'))
            
            # Aggressive anti-repetition for frequently ordered items
            repetition_penalty = 0
            should_exclude = False
            
            if food_id in ordered_items:
                order_count = ordered_items[food_id]
                
                if order_count >= 8:  # Completely exclude items ordered 8+ times
                    should_exclude = True
                    logger.debug(f"EXCLUDED: {food.get('name', 'Unknown')} - ordered {order_count} times")
                elif order_count >= 6:  # Very heavy penalty for 6-7 orders
                    repetition_penalty = order_count * 0.8  # Much stronger penalty
                elif order_count >= 4:  # Heavy penalty for 4-5 orders  
                    repetition_penalty = order_count * 0.5
                elif order_count >= 2:  # Moderate penalty for 2-3 orders
                    repetition_penalty = order_count * 0.2
            
            # Skip this food if it should be excluded
            if should_exclude:
                continue
            
            preference_score = 0
            matched_preferences = []
            
            # Score based on user's learned ingredient preferences
            food_text = food.get('ingredients', '') or food.get('description', '')
            if food_text:
                food_text_lower = food_text.lower()
                
                # Check for each preferred ingredient
                for preferred_ingredient, user_count in top_preferences:
                    if preferred_ingredient in food_text_lower:
                        # Weight by how much user loves this ingredient
                        ingredient_score = user_count * 1.0  # Strong preference weighting
                        preference_score += ingredient_score
                        matched_preferences.append(f"{preferred_ingredient}({user_count})")
                        
                        logger.debug(f"Food '{food.get('name', 'Unknown')}' matches '{preferred_ingredient}' (+{ingredient_score})")
            
            # Bonus for multiple preferred ingredients in same dish
            if len(matched_preferences) > 1:
                preference_score += len(matched_preferences) * 2  # Multi-ingredient bonus
            
            # Apply repetition penalty
            original_score = preference_score
            preference_score = max(0, preference_score - repetition_penalty)
            
            # Log penalty application for debugging
            if repetition_penalty > 0 and food_id in ordered_items:
                order_count = ordered_items[food_id]
                logger.debug(f"PENALTY: {food.get('name', 'Unknown')} - ordered {order_count}x, "
                           f"score {original_score:.1f} → {preference_score:.1f} (penalty: {repetition_penalty:.1f})")
            
            # Only recommend foods with actual preference matches
            if preference_score > 0:
                food_copy = food.copy()
                food_copy['preference_score'] = preference_score
                food_copy['matched_preferences'] = matched_preferences
                
                # Create preference-based recommendation reason
                if matched_preferences:
                    top_matches = matched_preferences[:3]
                    food_copy['recommendation_reason'] = f"You love: {', '.join([match.split('(')[0] for match in top_matches])}"
                else:
                    food_copy['recommendation_reason'] = f"Based on your taste profile"
                
                recommendations.append(food_copy)
        
        # Sort by preference score (highest user preference match first)
        recommendations.sort(key=lambda x: x.get('preference_score', 0), reverse=True)
        top_recommendations = recommendations[:top_n]
        
        logger.info(f"Generated {len(top_recommendations)} user-preference-based recommendations")
        for i, rec in enumerate(top_recommendations[:3], 1):
            logger.info(f"  {i}. {rec.get('name', 'Unknown')} (score: {rec.get('preference_score', 0):.1f}) - {rec.get('recommendation_reason', '')}")
        
        return top_recommendations

    def get_cold_start_recommendations(self, current_hour: Optional[int] = None, top_n: int = 8) -> List[Dict]:
        """
        Cold-start recommendations based on time-of-day filtering + popularity ranking
        
        Args:
            current_hour: Current hour (0-23), defaults to system time
            top_n: Number of recommendations to return
            
        Returns:
            List of time-appropriate food recommendations
        """
        from database import get_food_database
        
        if current_hour is None:
            current_hour = datetime.now().hour
        
        # Determine meal category based on time
        if 6 <= current_hour <= 10:
            target_meal = 'breakfast'
        elif 11 <= current_hour <= 15:
            target_meal = 'lunch'
        elif 16 <= current_hour <= 22:
            target_meal = 'dinner'
        else:
            target_meal = 'dinner'  # Late night default
        
        logger.info(f"Cold-start recommendation for {target_meal} at hour {current_hour}")
        
        # Filter foods by predicted meal category
        meal_appropriate_foods = []
        for food in self.food_data:
            food_name = food.get('name', '')
            ingredients = food.get('ingredients', '') or food.get('description', '')
            
            predicted_category = self.classify_meal_category(food_name, ingredients)
            if predicted_category == target_meal:
                meal_appropriate_foods.append(food)
        
        # Rank by real popularity from database instead of mock data
        db = get_food_database()
        for food in meal_appropriate_foods:
            food_id = str(food.get('_id'))
            stats = db.get_interaction_stats(food_id)
            
            # Calculate real popularity score based on orders and ratings
            order_count = stats.get('orders', 0)
            avg_rating = stats.get('avg_rating', 3.5)
            
            # Weighted popularity: 70% orders, 30% rating
            popularity_score = (order_count * 0.7) + (avg_rating * 6 * 0.3)
            food['popularity_score'] = popularity_score
            food['order_count'] = order_count
            food['avg_rating'] = avg_rating
        
        # Sort by real popularity and take top N
        meal_appropriate_foods.sort(key=lambda x: x.get('popularity_score', 0), reverse=True)
        top_foods = meal_appropriate_foods[:top_n]
        
        # Add recommendation metadata
        recommendations = []
        for food in top_foods:
            food_copy = food.copy()
            order_count = food_copy.get('order_count', 0)
            
            # More descriptive reason based on actual data
            if order_count >= 50:
                food_copy['recommendation_reason'] = f"Bestseller for {target_meal}"
            elif order_count >= 20:
                food_copy['recommendation_reason'] = f"Popular {target_meal} choice"
            elif order_count >= 5:
                food_copy['recommendation_reason'] = f"Recommended for {target_meal}"
            else:
                food_copy['recommendation_reason'] = f"Perfect for {target_meal}"
            
            food_copy['meal_category'] = target_meal
            recommendations.append(food_copy)
        
        logger.info(f"Generated {len(recommendations)} cold-start recommendations for {target_meal} using real order data")
        return recommendations

    def reset_model_state(self):
        """
        Reset content-based recommender model state for fresh training
        
        Returns:
            Dict with reset operation details
        """
        try:
            # Reset TF-IDF models and similarity matrices
            original_tfidf_foods = len(getattr(self, 'tfidf_matrix', []))
            
            # Clear TF-IDF components
            self.tfidf_matrix = None
            self.tfidf_vectorizer = None
            self.food_data = []
            self.ingredient_processor = IngredientProcessor()
            
            # Clear any cached similarity data
            if hasattr(self, 'similarity_cache'):
                self.similarity_cache = {}
            
            # Clear meal classifier cache
            if hasattr(self, 'meal_classifier_cache'):
                self.meal_classifier_cache = {}
            
            logger.info(f"Content-based model state reset - cleared {original_tfidf_foods} food TF-IDF vectors")
            
            return {
                'model_type': 'content_based',
                'tfidf_vectors_cleared': original_tfidf_foods,
                'ingredient_processor_reset': True,
                'cache_cleared': True,
                'requires_retraining': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error resetting content-based model state: {e}")
            return {'error': str(e)}

# Singleton instance
content_recommender = ContentBasedRecommender()

def get_content_recommender():
    """Get the global content-based recommender instance"""
    return content_recommender