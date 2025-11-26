"""
Routing Service Flask API
=========================
Provides routing endpoints for shipperMobile app
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from datetime import datetime
import os
import json

from osm_map_loader import get_map_loader
from smart_router import get_router, SmartRouter
from dispatcher import ShipperDispatcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global state
map_loader = None
router = None
dispatcher = None

def initialize_routing_service():
    """Initialize the routing service with OSM data"""
    global map_loader, router, dispatcher
    
    logger.info("Initializing Routing Service...")
    
    # Load map data
    map_loader = get_map_loader()
    
    # Download Ho Chi Minh City map (or load from cache)
    # You can adjust this to download a specific bounding box instead
    graph = map_loader.download_city_graph(
        city_name="Ho Chi Minh City, Vietnam",
        network_type='drive',  # For motorcycles/cars
        simplify=True
    )
    
    # Initialize router with the graph
    router = get_router(graph)
    
    # Initialize dispatcher
    dispatcher = ShipperDispatcher(router)
    
    logger.info("✅ Routing Service ready!")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'OSM Routing Service',
        'map_loaded': router is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/map/info', methods=['GET'])
def get_map_info():
    """Get information about the loaded map"""
    if map_loader is None:
        return jsonify({'error': 'Map not loaded'}), 500
    
    info = map_loader.get_graph_info()
    return jsonify({
        'success': True,
        'map_info': info,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/route/calculate', methods=['POST'])
def calculate_route():
    """
    Calculate route between two points
    
    Request body:
    {
        "start": {"lat": 10.7769, "lon": 106.7009},
        "end": {"lat": 10.7829, "lon": 106.6958},
        "use_smart_routing": true  // Optional: use learned patterns
    }
    """
    if router is None:
        return jsonify({'error': 'Router not initialized'}), 500
    
    try:
        data = request.get_json()
        
        # Validate input
        if 'start' not in data or 'end' not in data:
            return jsonify({'error': 'Missing start or end coordinates'}), 400
        
        start = data['start']
        end = data['end']
        
        if 'lat' not in start or 'lon' not in start:
            return jsonify({'error': 'Invalid start coordinates'}), 400
        if 'lat' not in end or 'lon' not in end:
            return jsonify({'error': 'Invalid end coordinates'}), 400
        
        # Optional parameters
        use_smart_routing = data.get('use_smart_routing', False)
        
        # Calculate route
        result = router.calculate_route(
            start_lat=start['lat'],
            start_lon=start['lon'],
            end_lat=end['lat'],
            end_lon=end['lon'],
            use_learned_patterns=use_smart_routing,
            current_time=datetime.now()
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/geocode/nearest-node', methods=['POST'])
def get_nearest_node():
    """
    Find nearest road node to given coordinates
    
    Request body:
    {
        "lat": 10.7769,
        "lon": 106.7009
    }
    """
    if router is None:
        return jsonify({'error': 'Router not initialized'}), 500
    
    try:
        data = request.get_json()
        lat = data.get('lat')
        lon = data.get('lon')
        
        if lat is None or lon is None:
            return jsonify({'error': 'Missing lat or lon'}), 400
        
        node_id = router.find_nearest_node(lat, lon)
        
        # Get node coordinates
        node_data = router.graph.nodes[node_id]
        
        return jsonify({
            'success': True,
            'node_id': int(node_id),
            'coordinates': {
                'lat': node_data['y'],
                'lon': node_data['x']
            }
        })
        
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# DASHBOARD & SHIPPER MANAGEMENT ENDPOINTS
# ============================================

@app.route('/')
def dashboard():
    """Serve the admin dashboard"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (shippers_data.json, etc.)"""
    return send_from_directory('.', filename)

@app.route('/dispatch/shippers', methods=['GET'])
def get_shippers():
    """Get all shippers from MongoDB"""
    try:
        import requests
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:5137')
        response = requests.get(f'{backend_url}/api/shipper/all', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)
        
        return jsonify({
            'success': False,
            'error': 'Failed to fetch shippers from MongoDB'
        }), 500
    except Exception as e:
        logger.error(f"Error loading shippers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/dispatch/generate-shippers', methods=['POST'])
def generate_shippers_endpoint():
    """Generate new random shippers - requires backend server"""
    return jsonify({
        'success': False,
        'error': 'Shipper generation now handled by backend server. Use POST /api/shipper/register instead.'
    }), 400

@app.route('/dispatch/assign', methods=['POST'])
def assign_order():
    """Find nearest shipper and assign order"""
    try:
        data = request.json
        
        order_id = data.get('order_id')
        shop_location = data.get('shop_location')
        customer_location = data.get('customer_location')
        
        if not all([order_id, shop_location, customer_location]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find and assign nearest shipper
        assignment = dispatcher.assign_order_to_shipper(
            order_id=order_id,
            shop_location=shop_location,
            customer_location=customer_location
        )
        
        if assignment:
            return jsonify({
                'success': True,
                'assignment': assignment
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No available shipper found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error assigning order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/dispatch/find-nearest', methods=['POST'])
def find_nearest_shipper():
    """Find nearest available shipper to shop"""
    try:
        data = request.json
        
        shop_lat = data.get('shop_lat')
        shop_lon = data.get('shop_lon')
        max_distance = data.get('max_distance_km', 10)
        
        if shop_lat is None or shop_lon is None:
            return jsonify({'error': 'Missing shop coordinates'}), 400
        
        shop_location = {'lat': shop_lat, 'lon': shop_lon}
        
        # Find nearest shippers
        nearest_shippers = dispatcher.find_nearest_shipper(
            shop_location=shop_location,
            max_distance_km=max_distance
        )
        
        if nearest_shippers:
            return jsonify({
                'success': True,
                'shippers': nearest_shippers
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No available shipper found within range'
            }), 404
            
    except Exception as e:
        logger.error(f"Error finding nearest shipper: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/dispatch/shipper-status', methods=['POST'])
def update_shipper_status():
    """Update shipper status - proxy to backend"""
    try:
        import requests
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:5137')
        
        # Forward request to backend
        response = requests.post(
            f'{backend_url}/api/shipper/update-status',
            json=request.json,
            timeout=5
        )
        
        return jsonify(response.json()), response.status_code
            
    except Exception as e:
        logger.error(f"Error updating shipper status: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize routing service before starting server
    initialize_routing_service()
    
    # Start Flask server
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5001))
    
    logger.info(f"Starting Routing Service API on {host}:{port}")
    
    # Print clickable URLs
    print("\n" + "="*60)
    print("SHIPPER DISPATCH SYSTEM")
    print("="*60)
    print(f"Dashboard:  http://localhost:{port}")
    print(f"API:        http://localhost:{port}/health")
    print(f"Map View:   http://localhost:{port}/")
    print("="*60)
    print("Ctrl+Click on the URL to open in browser")
    print("="*60 + "\n")
    
    app.run(host=host, port=port, debug=True)
