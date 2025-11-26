"""
Data Generation Script for Food Recommendation System
=====================================================

This script generates realistic, simulated user and order data to train
the recommendation model. It creates users, simulates their ordering behavior,
and sends the data to the API's tracking endpoints.

Usage:
1. Make sure the Flask API server is running (`python app.py`).
2. Run this script: `python generate_demo_data.py`
"""
import requests
import random
import json
from faker import Faker

# --- Configuration ---
API_BASE = "http://localhost:8000"
NUM_USERS = 50  # Number of simulated users to create
MAX_ORDERS_PER_USER = 25  # Maximum number of orders each user can place
PREFERRED_CATEGORY_CHANCE = 0.6  # 60% chance a user will order from their favorite category

# Initialize Faker for data generation
fake = Faker()

def check_api_status():
    """Check if the Flask API is running before starting."""
    print("Checking API status...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print(f"✅ API is running and healthy at {API_BASE}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}. Please check the server.")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed. Is the Flask server running at {API_BASE}?")
        return False

def get_available_foods():
    """Fetch all available food items from the API."""
    print("Fetching available food menu...")
    try:
        response = requests.get(f"{API_BASE}/foods")
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            # Flatten the categorized food list into a single list
            all_foods = []
            for category, items in data.get('categories', {}).items():
                for item in items:
                    item['category'] = category
                    all_foods.append(item)
            print(f"✅ Found {len(all_foods)} food items across {len(data.get('categories'))} categories.")
            return all_foods, list(data.get('categories').keys())
        else:
            print("❌ Failed to get food data from API.")
            return [], []
    except Exception as e:
        print(f"❌ Error fetching foods: {e}")
        return [], []

def generate_users(num_users, categories):
    """Generate a list of simulated users with preferred categories."""
    print(f"Generating {num_users} simulated users...")
    users = []
    for i in range(num_users):
        user = {
            "user_id": f"sim_user_{i+1}",
            "name": fake.name(),
            "preferred_category": random.choice(categories) if categories else None
        }
        users.append(user)
    print(f"✅ {len(users)} users generated.")
    return users

def simulate_orders(users, foods, categories):
    """Simulate and track orders for each user."""
    if not foods:
        print("No food items available to simulate orders. Aborting.")
        return

    total_orders_simulated = 0
    print("\n🚀 Starting order simulation...")

    for user in users:
        num_orders = random.randint(5, MAX_ORDERS_PER_USER)
        print(f"  Simulating {num_orders} orders for {user['name']} (Prefers: {user['preferred_category']})...")

        for _ in range(num_orders):
            # Decide if the user orders from their preferred category or randomly
            if user['preferred_category'] and random.random() < PREFERRED_CATEGORY_CHANCE:
                # Order from preferred category
                possible_items = [f for f in foods if f['category'] == user['preferred_category']]
            else:
                # Order from any category
                possible_items = foods
            
            if not possible_items:
                continue

            # Create an order with 1 to 3 items
            order_items_count = random.randint(1, 3)
            order_items = random.sample(possible_items, min(order_items_count, len(possible_items)))

            # Format for the API
            api_order_items = [{"food_id": item['id'], "quantity": 1} for item in order_items]
            order_value = sum(item['price'] for item in order_items)

            # Send the order to the tracking endpoint
            try:
                response = requests.post(
                    f"{API_BASE}/track/order",
                    json={
                        "user_id": user['user_id'],
                        "food_items": api_order_items,
                        "order_value": order_value
                    }
                )
                response.raise_for_status()
                total_orders_simulated += 1
            except Exception as e:
                print(f"    ❌ Error tracking order for user {user['user_id']}: {e}")

    print(f"\n✅ Simulation complete! {total_orders_simulated} total orders were sent to the API.")

def train_content_model():
    """Train the content-based model on the existing food data."""
    print("\nTraining content-based model...")
    try:
        response = requests.post(f"{API_BASE}/content-based/train")
        response.raise_for_status()
        result = response.json()
        if result.get('success'):
            print(f"✅ Content-based model trained successfully on {result.get('message', 'N/A').split('on ')[-1]}.")
            return True
        else:
            print(f"❌ Failed to train content-based model: {result.get('error')}")
            return False
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error sending train request: {e}")
        return False

def main():
    """Main function to run the data generation process."""
    print("--- Food Recommendation System: Data Generation Script ---")
    
    if not check_api_status():
        return

    if not train_content_model():
        print("Aborting data generation due to training failure.")
        return

    foods, categories = get_available_foods()
    if not foods or not categories:
        print("Could not retrieve food data. Please ensure the database has food items.")
        return

    users = generate_users(NUM_USERS, categories)
    
    simulate_orders(users, foods, categories)

    print("\n--- Data generation finished ---")
    print("The recommendation model has now been trained with simulated data.")

if __name__ == "__main__":
    main()
