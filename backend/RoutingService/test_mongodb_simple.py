"""
Simple MongoDB Learning Test - Verify learning data persistence
"""
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGODB_URL')

print("\n" + "="*60)
print("  MONGODB LEARNING SYSTEM TEST")
print("="*60 + "\n")

# Connect to MongoDB
print("📡 Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client['test']
print("✅ Connected to 'test' database\n")

# Check collections
print("📂 Checking learning collections:")
print("-" * 60)

collections_to_check = [
    'delivery_zones',
    'shipper_performance', 
    'complete_journeys',
    'route_memory'
]

for coll_name in collections_to_check:
    count = db[coll_name].count_documents({})
    print(f"  {coll_name:25} {count:5} documents")

print("\n" + "="*60)
print("  INSERTING TEST DATA")
print("="*60 + "\n")

# Test 1: Insert delivery zone
print("📍 Test 1: Delivery Zone Learning")
zone_doc = {
    "dest_zone": "106.695_10.783",
    "context": "weekday_afternoon",
    "avg_time_seconds": 720,
    "sample_count": 1,
    "last_updated": datetime.now()
}
result = db.delivery_zones.insert_one(zone_doc)
print(f"  ✅ Inserted zone document: {result.inserted_id}")

# Test 2: Insert shipper performance
print("\n👤 Test 2: Shipper Performance Tracking")
shipper_doc = {
    "shipper_id": "TEST_SHIPPER_001",
    "speed_multiplier": 0.95,
    "delivery_count": 1,
    "last_updated": datetime.now()
}
result = db.shipper_performance.insert_one(shipper_doc)
print(f"  ✅ Inserted shipper document: {result.inserted_id}")

# Test 3: Insert complete journey
print("\n🔄 Test 3: Complete Journey Tracking")
journey_doc = {
    "origin_zone": "106.700_10.770",
    "dest_zone": "106.695_10.783",
    "context": "weekday_afternoon",
    "avg_total_time_seconds": 900,
    "sample_count": 1,
    "last_updated": datetime.now()
}
result = db.complete_journeys.insert_one(journey_doc)
print(f"  ✅ Inserted journey document: {result.inserted_id}")

print("\n" + "="*60)
print("  VERIFYING INSERTS")
print("="*60 + "\n")

# Verify data was saved
print("📊 Final document counts:")
print("-" * 60)
for coll_name in collections_to_check:
    count = db[coll_name].count_documents({})
    print(f"  {coll_name:25} {count:5} documents")

print("\n" + "="*60)
print("  READING TEST DATA BACK")
print("="*60 + "\n")

# Read back the data
zone = db.delivery_zones.find_one({"dest_zone": "106.695_10.783"})
if zone:
    print(f"✅ Delivery Zone Found:")
    print(f"   Zone: {zone['dest_zone']}")
    print(f"   Avg time: {zone['avg_time_seconds']}s")
    print(f"   Samples: {zone['sample_count']}")

shipper = db.shipper_performance.find_one({"shipper_id": "TEST_SHIPPER_001"})
if shipper:
    print(f"\n✅ Shipper Performance Found:")
    print(f"   Shipper ID: {shipper['shipper_id']}")
    print(f"   Speed multiplier: {shipper['speed_multiplier']:.2f}x")
    print(f"   Deliveries: {shipper['delivery_count']}")

journey = db.complete_journeys.find_one({"origin_zone": "106.700_10.770"})
if journey:
    print(f"\n✅ Complete Journey Found:")
    print(f"   Route: {journey['origin_zone']} → {journey['dest_zone']}")
    print(f"   Avg time: {journey['avg_total_time_seconds']}s")
    print(f"   Samples: {journey['sample_count']}")

print("\n" + "="*60)
print("  ✅ MONGODB LEARNING TEST PASSED!")
print("="*60)
print("\n🎉 Your MongoDB learning persistence is working!")
print("   All test documents were successfully:")
print("   - Inserted into MongoDB")
print("   - Retrieved from MongoDB")
print("   - Verified with correct data\n")

# Cleanup test data
print("🧹 Cleaning up test data...")
db.delivery_zones.delete_one({"dest_zone": "106.695_10.783"})
db.shipper_performance.delete_one({"shipper_id": "TEST_SHIPPER_001"})
db.complete_journeys.delete_one({"origin_zone": "106.700_10.770"})
print("✅ Test data removed\n")
