"""
Shipper Dispatcher - Find Nearest Available Shipper
===================================================
Uses Dijkstra/A* algorithm to find closest shipper to shop location
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time
import requests
import os

from smart_router import get_router

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5137')

logger = logging.getLogger(__name__)

class ShipperDispatcher:
    """
    Dispatch system to assign orders to nearest available shippers
    """
    
    def __init__(self, router):
        """
        Initialize dispatcher with router instance
        
        Args:
            router: SmartRouter instance for calculating routes
        """
        self.router = router
        logger.info("Dispatcher initialized")
    
    def calculate_distance_to_shipper(self, shop_location: Dict, shipper_location: Dict) -> Optional[Dict]:
        """
        Calculate route from shipper to shop
        
        Args:
            shop_location: {'lat': float, 'lon': float}
            shipper_location: {'lat': float, 'lon': float}
            
        Returns:
            Route info or None if calculation fails
        """
        try:
            route = self.router.calculate_route(
                start_lat=shipper_location['lat'],
                start_lon=shipper_location['lon'],
                end_lat=shop_location['lat'],
                end_lon=shop_location['lon'],
                use_learned_patterns=False
            )
            return route
        except Exception as e:
            logger.error(f"Error calculating route: {e}")
            return None
    
    def get_available_shippers(self) -> List[Dict]:
        """
        Load all available shippers from MongoDB
        
        Returns:
            List of available shipper dictionaries
        """
        try:
            # Fetch from MongoDB via Node.js API
            response = requests.get(f'{BACKEND_URL}/api/shipper/available', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    shippers = data.get('shippers', [])
                    logger.info(f"Fetched {len(shippers)} available shippers from MongoDB")
                    return shippers
            
            logger.error(f"MongoDB API returned status {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch from MongoDB: {e}")
            return []
    
    def find_nearest_shipper(self, 
                            shop_location: Dict,
                            available_shippers: List[Dict] = None,
                            max_distance_km: float = 10.0) -> Optional[Dict]:
        """
        Find the nearest available shipper to shop using Dijkstra algorithm
        
        This is the core dispatch logic that:
        1. Calculates routes from ALL available shippers to the shop
        2. Uses YOUR A* algorithm (which is similar to Dijkstra) to find actual road distances
        3. Selects the shipper with shortest travel time
        
        Args:
            shop_location: {'lat': float, 'lon': float} - Restaurant pickup location
            available_shippers: List of shipper dicts with 'current_location' (if None, will load from file)
            max_distance_km: Maximum acceptable distance in kilometers
            
        Returns:
            Best shipper match with route details, or None if no suitable shipper
        """
        # Load available shippers if not provided
        if available_shippers is None:
            available_shippers = self.get_available_shippers()
        
        if not available_shippers:
            logger.warning("No available shippers")
            return None
        
        start_time = time.time()
        logger.info(f"Finding nearest shipper among {len(available_shippers)} candidates")
        
        # Calculate routes to all shippers (Dijkstra approach - test all paths)
        shipper_routes = []
        
        for shipper in available_shippers:
            shipper_location = shipper['current_location']
            
            # Calculate route using YOUR A* algorithm
            route_info = self.calculate_distance_to_shipper(shop_location, shipper_location)
            
            if route_info and route_info.get('success'):
                route = route_info['route']
                
                # Check distance constraint
                distance_km = route['distance_meters'] / 1000.0
                if distance_km <= max_distance_km:
                    shipper_routes.append({
                        'shipper': shipper,
                        'route': route,
                        'distance_km': distance_km,
                        'eta_seconds': route['estimated_time_seconds'],
                        'eta_minutes': round(route['estimated_time_seconds'] / 60.0, 1)
                    })
        
        if not shipper_routes:
            logger.warning(f"No shippers within {max_distance_km}km of shop")
            return None
        
        # Sort by travel time (fastest first) - This is the Dijkstra selection
        # We've calculated all paths, now pick the shortest one
        shipper_routes.sort(key=lambda x: x['eta_seconds'])
        
        best_match = shipper_routes[0]
        
        calc_time = time.time() - start_time
        
        logger.info(
            f"Found nearest shipper: {best_match['shipper']['shipper_id']} "
            f"({best_match['shipper']['name']}) - "
            f"{best_match['distance_km']:.2f}km, "
            f"ETA: {best_match['eta_minutes']} min "
            f"(calculated in {calc_time:.2f}s)"
        )
        
        return best_match
    
    def assign_order_to_shipper(self,
                                order_id: str,
                                shop_location: Dict,
                                customer_location: Dict,
                                available_shippers: List[Dict] = None) -> Optional[Dict]:
        """
        Complete order assignment workflow
        
        Args:
            order_id: Unique order identifier
            shop_location: Restaurant pickup location
            customer_location: Delivery destination
            available_shippers: List of available shippers (if None, will load from file)
            
        Returns:
            Assignment details with shipper and route info
        """
        # Load available shippers if not provided
        if available_shippers is None:
            available_shippers = self.get_available_shippers()
        
        logger.info(f"Assigning order {order_id}")
        
        # Step 1: Find nearest shipper to shop
        nearest = self.find_nearest_shipper(shop_location, available_shippers)
        
        if not nearest:
            logger.error(f"Failed to assign order {order_id} - no suitable shipper")
            return None
        
        # Step 2: Calculate route from shop to customer (for info only)
        shop_to_customer = self.router.calculate_route(
            start_lat=shop_location['lat'],
            start_lon=shop_location['lon'],
            end_lat=customer_location['lat'],
            end_lon=customer_location['lon']
        )
        
        # Step 3: Create assignment
        assignment = {
            'order_id': order_id,
            'shipper_id': nearest['shipper']['shipper_id'],
            'shipper_name': nearest['shipper']['name'],
            'shipper_phone': nearest['shipper']['phone'],
            
            # Route from shipper to shop (pickup)
            'route_to_shop': {
                'coordinates': nearest['route']['coordinates'],
                'distance_meters': nearest['route']['distance_meters'],
                'distance_km': nearest['distance_km'],
                'eta_seconds': nearest['route']['estimated_time_seconds'],
                'eta_minutes': nearest['eta_minutes']
            },
            
            # Route from shop to customer (delivery) - for display only
            'route_to_customer': {
                'distance_meters': shop_to_customer['route']['distance_meters'],
                'distance_km': round(shop_to_customer['route']['distance_meters'] / 1000.0, 2),
                'eta_seconds': shop_to_customer['route']['estimated_time_seconds'],
                'eta_minutes': round(shop_to_customer['route']['estimated_time_seconds'] / 60.0, 1)
            } if shop_to_customer.get('success') else None,
            
            'shop_location': shop_location,
            'customer_location': customer_location,
            'assigned_at': datetime.now().isoformat(),
            'status': 'assigned'
        }
        
        logger.info(
            f"✅ Order {order_id} assigned to {assignment['shipper_name']} "
            f"(Pickup: {assignment['route_to_shop']['eta_minutes']}min)"
        )
        
        return assignment


# Singleton instance
_dispatcher = None

def get_dispatcher(router=None):
    """Get singleton dispatcher instance"""
    global _dispatcher
    if _dispatcher is None:
        if router is None:
            from smart_router import get_router
            router = get_router()
        _dispatcher = ShipperDispatcher(router)
    return _dispatcher


if __name__ == "__main__":
    """Test dispatcher with generated shippers"""
    print("🚀 Dispatcher Test\n")
    
    # Import dependencies
    from shipper_generator import get_generator
    from osm_map_loader import get_map_loader
    from smart_router import get_router
    
    # Load map and initialize router
    print("Loading map data...")
    map_loader = get_map_loader()
    graph = map_loader.download_city_graph("Ho Chi Minh City, Vietnam")
    router = get_router(graph)
    
    # Load test shippers
    print("\nLoading test shippers...")
    generator = get_generator()
    shippers = generator.load_from_file()
    
    if not shippers:
        print("Generating new shippers...")
        shippers = generator.generate_shippers(count=15)
        generator.save_to_file(shippers)
    
    available = generator.get_available_shippers(shippers)
    
    # Test shop location (District 1 - central HCM)
    shop_location = {'lat': 10.7769, 'lon': 106.7009}
    customer_location = {'lat': 10.7829, 'lon': 106.6958}
    
    print(f"\n📍 Shop: District 1 ({shop_location['lat']}, {shop_location['lon']})")
    print(f"📍 Customer: ({customer_location['lat']}, {customer_location['lon']})")
    
    # Initialize dispatcher
    dispatcher = get_dispatcher(router)
    
    # Find nearest shipper
    print("\n" + "="*60)
    assignment = dispatcher.assign_order_to_shipper(
        order_id="TEST_ORDER_001",
        shop_location=shop_location,
        customer_location=customer_location,
        available_shippers=available
    )
    
    if assignment:
        print("\n✅ ASSIGNMENT SUCCESSFUL")
        print("="*60)
        print(f"Order ID: {assignment['order_id']}")
        print(f"Shipper: {assignment['shipper_name']} ({assignment['shipper_id']})")
        print(f"Phone: {assignment['shipper_phone']}")
        print(f"\n📍 Pickup Route (Shipper → Shop):")
        print(f"   Distance: {assignment['route_to_shop']['distance_km']:.2f} km")
        print(f"   ETA: {assignment['route_to_shop']['eta_minutes']} minutes")
        print(f"\n📍 Delivery Route (Shop → Customer):")
        if assignment['route_to_customer']:
            print(f"   Distance: {assignment['route_to_customer']['distance_km']:.2f} km")
            print(f"   ETA: {assignment['route_to_customer']['eta_minutes']} minutes")
    else:
        print("\n❌ Assignment failed - no suitable shipper found")
