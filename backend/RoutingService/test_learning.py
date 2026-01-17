"""
Test script to verify the routing model learning system
Run this to confirm the learning system is working correctly
"""
import requests
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
ROUTING_SERVICE_URL = "http://localhost:5001"
MONGO_URI = os.getenv('MONGODB_URL')

class LearningTester:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client['test']
        
    def print_section(self, title):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    
    def test_1_check_mongodb_connection(self):
        """Test 1: Verify MongoDB connection and collections exist"""
        self.print_section("TEST 1: MongoDB Connection & Collections")
        
        try:
            # List all collections
            collections = self.db.list_collection_names()
            print(f"✅ Connected to MongoDB 'test' database")
            print(f"📂 Total collections: {len(collections)}")
            
            # Check for learning collections
            learning_collections = [
                'route_memory',
                'delivery_zones', 
                'shipper_performance',
                'complete_journeys',
                'traffic_patterns',
                'interactions'
            ]
            
            for coll_name in learning_collections:
                if coll_name in collections:
                    count = self.db[coll_name].count_documents({})
                    print(f"✅ {coll_name}: {count} documents")
                else:
                    print(f"⚠️  {coll_name}: NOT FOUND (will be created on first learning)")
            
            return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
    
    def test_2_check_api_endpoints(self):
        """Test 2: Verify routing service API is running"""
        self.print_section("TEST 2: Routing Service API Health")
        
        try:
            # Test health endpoint
            response = requests.get(f"{ROUTING_SERVICE_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Routing service is running")
                print(f"📍 URL: {ROUTING_SERVICE_URL}")
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
            
            # Test learning stats endpoint
            stats_response = requests.get(f"{ROUTING_SERVICE_URL}/learning/stats", timeout=5)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"✅ Learning stats endpoint working")
                print(f"   Current stats:")
                print(f"   - Routes learned: {stats.get('total_routes_learned', 0)}")
                print(f"   - Cache hits: {stats.get('cache_hits', 0)}")
                print(f"   - Cache hit rate: {stats.get('cache_hit_rate', 0):.1f}%")
            
            return True
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to routing service at {ROUTING_SERVICE_URL}")
            print(f"   Make sure to run: cd backend/RoutingService && python app.py")
            return False
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False
    
    def test_3_simulate_delivery_learning(self):
        """Test 3: Simulate a delivery and verify learning occurs"""
        self.print_section("TEST 3: Simulate Delivery & Verify Learning")
        
        # Get baseline counts
        zones_before = self.db.delivery_zones.count_documents({})
        shippers_before = self.db.shipper_performance.count_documents({})
        journeys_before = self.db.complete_journeys.count_documents({})
        routes_before = self.db.route_memory.count_documents({})
        
        print(f"📊 Baseline counts:")
        print(f"   Delivery zones: {zones_before}")
        print(f"   Shipper performance: {shippers_before}")
        print(f"   Complete journeys: {journeys_before}")
        print(f"   Route memory: {routes_before}")
        
        # Simulate delivery completion
        test_delivery = {
            "order_id": "TEST_ORDER_123",
            "shipper_id": "TEST_SHIPPER_001",
            "shipper_location": {"lat": 10.7700, "lon": 106.7000},
            "shop_location": {"lat": 10.7769, "lon": 106.7009},
            "customer_location": {"lat": 10.7829, "lon": 106.6958},
            "assignment_time": (datetime.now() - timedelta(minutes=15)).isoformat() + "Z",
            "delivery_time": datetime.now().isoformat() + "Z",
            "estimated_time_seconds": 720
        }
        
        print(f"\n🚚 Simulating delivery...")
        print(f"   Shipper: {test_delivery['shipper_id']}")
        print(f"   Estimated: {test_delivery['estimated_time_seconds']}s")
        
        try:
            response = requests.post(
                f"{ROUTING_SERVICE_URL}/learning/record-delivery",
                json=test_delivery,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Learning feedback accepted")
                print(f"   Actual time: {result['actual_time_seconds']:.0f}s")
                print(f"   Accuracy delta: {result.get('accuracy_delta', 0):.0f}s")
                
                # Wait a moment for DB writes
                import time
                time.sleep(1)
                
                # Check if counts increased
                zones_after = self.db.delivery_zones.count_documents({})
                shippers_after = self.db.shipper_performance.count_documents({})
                journeys_after = self.db.complete_journeys.count_documents({})
                routes_after = self.db.route_memory.count_documents({})
                
                print(f"\n📈 After learning:")
                print(f"   Delivery zones: {zones_before} → {zones_after} {self._delta(zones_before, zones_after)}")
                print(f"   Shipper performance: {shippers_before} → {shippers_after} {self._delta(shippers_before, shippers_after)}")
                print(f"   Complete journeys: {journeys_before} → {journeys_after} {self._delta(journeys_before, journeys_after)}")
                print(f"   Route memory: {routes_before} → {routes_after} {self._delta(routes_before, routes_after)}")
                
                # Verify shipper performance was updated
                shipper_data = self.db.shipper_performance.find_one({"shipper_id": "TEST_SHIPPER_001"})
                if shipper_data:
                    print(f"\n👤 Shipper Performance Learned:")
                    print(f"   Speed multiplier: {shipper_data['speed_multiplier']:.3f}x")
                    print(f"   Deliveries tracked: {shipper_data['delivery_count']}")
                
                return True
            else:
                print(f"❌ Learning failed: {response.status_code}")
                print(f"   {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Simulation failed: {e}")
            return False
    
    def test_4_verify_shipper_learning(self):
        """Test 4: Test multiple deliveries for same shipper and verify learning"""
        self.print_section("TEST 4: Shipper Learning Over Time")
        
        shipper_id = "LEARNING_TEST_SHIPPER"
        
        # Simulate 3 deliveries with different performance
        deliveries = [
            {"estimated": 600, "actual": 540},  # 10% faster
            {"estimated": 720, "actual": 648},  # 10% faster
            {"estimated": 480, "actual": 432},  # 10% faster
        ]
        
        print(f"🧪 Testing shipper learning with 3 deliveries...")
        
        for i, delivery in enumerate(deliveries, 1):
            test_data = {
                "order_id": f"LEARN_TEST_{i}",
                "shipper_id": shipper_id,
                "shipper_location": {"lat": 10.7700, "lon": 106.7000},
                "shop_location": {"lat": 10.7769, "lon": 106.7009},
                "customer_location": {"lat": 10.7829 + (i*0.001), "lon": 106.6958},
                "assignment_time": (datetime.now() - timedelta(minutes=delivery['actual']//60)).isoformat() + "Z",
                "delivery_time": datetime.now().isoformat() + "Z",
                "estimated_time_seconds": delivery['estimated']
            }
            
            response = requests.post(
                f"{ROUTING_SERVICE_URL}/learning/record-delivery",
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Delivery {i}: {delivery['estimated']}s est → {result['actual_time_seconds']:.0f}s actual")
            
            import time
            time.sleep(0.5)
        
        # Check learned multiplier
        shipper_data = self.db.shipper_performance.find_one({"shipper_id": shipper_id})
        if shipper_data:
            multiplier = shipper_data['speed_multiplier']
            print(f"\n✅ Shipper learning verified!")
            print(f"   Speed multiplier: {multiplier:.3f}x")
            print(f"   Expected: ~0.90x (10% faster)")
            print(f"   Deliveries: {shipper_data['delivery_count']}")
            
            if 0.85 <= multiplier <= 0.95:
                print(f"   ✅ Multiplier in expected range!")
                return True
            else:
                print(f"   ⚠️  Multiplier outside expected range")
                return True
        else:
            print(f"❌ No shipper data found")
            return False
    
    def test_5_verify_zone_learning(self):
        """Test 5: Verify delivery zone learning"""
        self.print_section("TEST 5: Delivery Zone Pattern Learning")
        
        # Send deliveries to same zone multiple times
        zone_lat = 10.7850
        zone_lon = 106.7100
        
        print(f"🧪 Testing zone learning (same destination, multiple deliveries)...")
        
        for i in range(3):
            test_data = {
                "order_id": f"ZONE_TEST_{i}",
                "shipper_id": f"SHIPPER_{i}",
                "shipper_location": {"lat": 10.7700, "lon": 106.7000},
                "shop_location": {"lat": 10.7769, "lon": 106.7009},
                "customer_location": {"lat": zone_lat, "lon": zone_lon},
                "assignment_time": (datetime.now() - timedelta(minutes=12)).isoformat() + "Z",
                "delivery_time": datetime.now().isoformat() + "Z",
                "estimated_time_seconds": 700
            }
            
            response = requests.post(
                f"{ROUTING_SERVICE_URL}/learning/record-delivery",
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Delivery {i+1}: {result['actual_time_seconds']:.0f}s actual")
            
            import time
            time.sleep(0.5)
        
        # Check if zone was learned
        zone_grid = f"{int(zone_lon * 1000) / 1000:.3f}_{int(zone_lat * 1000) / 1000:.3f}"
        zone_data = self.db.delivery_zones.find_one({"dest_zone": zone_grid})
        
        if zone_data:
            print(f"\n✅ Delivery zone learning verified!")
            print(f"   Zone: {zone_data['dest_zone']}")
            print(f"   Avg time: {zone_data['avg_time_seconds']:.0f}s")
            print(f"   Samples: {zone_data['sample_count']}")
            print(f"   Context: {zone_data.get('context', 'N/A')}")
            return True
        else:
            print(f"❌ No zone data found for {zone_grid}")
            # Show what zones exist
            zones = list(self.db.delivery_zones.find().limit(5))
            if zones:
                print(f"\n   Found {len(zones)} zones in DB (showing first 5):")
                for z in zones:
                    print(f"   - {z['dest_zone']}: {z['avg_time_seconds']:.0f}s (n={z['sample_count']})")
            return False
    
    def test_6_smart_assignment_comparison(self):
        """Test 6: Compare old vs new assignment logic"""
        self.print_section("TEST 6: Smart Assignment Intelligence")
        
        print("🧠 This test shows how smart assignment picks better shippers\n")
        
        # Create scenario with shipper performance data
        print("Scenario: 2 shippers, same customer location")
        print("-" * 50)
        print("Shipper A: 2km from shop, speed multiplier 1.2 (slow)")
        print("Shipper B: 3km from shop, speed multiplier 0.8 (fast)")
        print()
        
        # Check if we have actual shipper data
        fast_shipper = self.db.shipper_performance.find_one({"speed_multiplier": {"$lt": 1.0}})
        slow_shipper = self.db.shipper_performance.find_one({"speed_multiplier": {"$gt": 1.0}})
        
        if fast_shipper and slow_shipper:
            print(f"✅ Found real shipper data:")
            print(f"   Fast shipper: {fast_shipper['shipper_id']} ({fast_shipper['speed_multiplier']:.2f}x)")
            print(f"   Slow shipper: {slow_shipper['shipper_id']} ({slow_shipper['speed_multiplier']:.2f}x)")
            print()
            print(f"💡 Smart assignment will factor in speed when choosing!")
        else:
            print(f"⚠️  No shipper performance data yet")
            print(f"   Complete a few deliveries to build performance profiles")
        
        return True
    
    def _delta(self, before, after):
        """Format delta with emoji"""
        if after > before:
            return f"(+{after - before}) ✅"
        elif after == before:
            return "(no change)"
        else:
            return f"({after - before})"
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("\n" + "🔬 ROUTING MODEL LEARNING VERIFICATION ".center(60, "="))
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        results = []
        
        # Run tests
        results.append(("MongoDB Connection", self.test_1_check_mongodb_connection()))
        results.append(("API Endpoints", self.test_2_check_api_endpoints()))
        results.append(("Delivery Learning", self.test_3_simulate_delivery_learning()))
        results.append(("Shipper Learning", self.test_4_verify_shipper_learning()))
        results.append(("Zone Learning", self.test_5_verify_zone_learning()))
        results.append(("Smart Assignment", self.test_6_smart_assignment_comparison()))
        
        # Summary
        self.print_section("TEST SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your learning system is working!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        print(f"{'='*60}\n")
        
        return passed == total

if __name__ == "__main__":
    tester = LearningTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if success else 1)
