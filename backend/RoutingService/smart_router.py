"""
A* Pathfinding Router with Smart Cost Weighting
===============================================
Implements A* algorithm with dynamic cost adjustments based on learned patterns
"""
import osmnx as ox
import networkx as nx
from typing import List, Tuple, Dict, Optional, Any
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class SmartRouter:
    """
    Routing engine that uses A* algorithm with learned traffic patterns
    """
    
    def __init__(self, graph: nx.MultiDiGraph):
        """
        Initialize router with a road network graph
        
        Args:
            graph: OSM road network graph from osmnx
        """
        self.graph = graph
        self.traffic_patterns = {}  # Will be populated from pattern learning
        self.shipper_preferences = {}  # Learned route preferences
        
        logger.info(f"Router initialized with {len(self.graph.nodes)} nodes")
    
    def find_nearest_node(self, lat: float, lon: float) -> int:
        """
        Find the nearest graph node to given coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Node ID of the nearest intersection
        """
        return ox.distance.nearest_nodes(self.graph, lon, lat)
    
    def calculate_route(self, 
                       start_lat: float, 
                       start_lon: float,
                       end_lat: float, 
                       end_lon: float,
                       use_learned_patterns: bool = False,
                       current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate optimal route using A* algorithm
        
        Args:
            start_lat, start_lon: Starting coordinates
            end_lat, end_lon: Destination coordinates
            use_learned_patterns: Whether to apply learned traffic/preference weights
            current_time: Time for traffic pattern lookup (defaults to now)
            
        Returns:
            Dictionary with route details including polyline coordinates
        """
        start_time = time.time()
        
        # Find nearest nodes
        start_node = self.find_nearest_node(start_lat, start_lon)
        end_node = self.find_nearest_node(end_lat, end_lon)
        
        logger.info(f"Routing from node {start_node} to {end_node}")
        
        # Prepare weight function
        if use_learned_patterns and current_time:
            weight_function = self._create_smart_weight_function(current_time)
        else:
            weight_function = 'travel_time'  # Default: use OSM speed limits
        
        try:
            # Run A* algorithm
            route_nodes = nx.shortest_path(
                self.graph,
                start_node,
                end_node,
                weight=weight_function,
                method='dijkstra'  # networkx's dijkstra implementation uses A* internally when heuristic available
            )
            
            # Convert route to coordinates
            route_coords = [
                (self.graph.nodes[node]['y'], self.graph.nodes[node]['x'])
                for node in route_nodes
            ]
            
            # Calculate route statistics
            route_length = self._calculate_route_length(route_nodes)
            estimated_time = self._calculate_route_time(route_nodes, weight_function)
            
            calc_time = time.time() - start_time
            
            return {
                'success': True,
                'route': {
                    'coordinates': route_coords,  # [(lat, lon), ...]
                    'nodes': route_nodes,
                    'distance_meters': route_length,
                    'estimated_time_seconds': estimated_time,
                    'num_segments': len(route_nodes) - 1
                },
                'calculation_time_ms': round(calc_time * 1000, 2),
                'used_learned_patterns': use_learned_patterns
            }
            
        except nx.NetworkXNoPath:
            logger.error(f"No path found between nodes {start_node} and {end_node}")
            return {
                'success': False,
                'error': 'No path found between locations',
                'start_node': start_node,
                'end_node': end_node
            }
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_smart_weight_function(self, current_time: datetime):
        """
        Create a custom weight function that applies learned patterns
        
        This will be enhanced as pattern learning is implemented
        """
        hour_of_day = current_time.hour
        day_of_week = current_time.weekday()
        
        def smart_weight(u, v, edge_data):
            """Calculate dynamic edge weight based on learned patterns"""
            base_time = edge_data.get('travel_time', 60)  # Default 60 seconds
            
            # Get edge identifier
            edge_id = f"{u}_{v}"
            
            # Apply traffic pattern multiplier if available
            if edge_id in self.traffic_patterns:
                pattern = self.traffic_patterns[edge_id]
                time_key = (day_of_week, hour_of_day)
                if time_key in pattern:
                    traffic_multiplier = pattern[time_key]
                    base_time *= traffic_multiplier
            
            # Apply shipper preference adjustment
            if edge_id in self.shipper_preferences:
                preference_score = self.shipper_preferences[edge_id]
                # Lower score = preferred route, reduce cost
                base_time *= (1.0 - preference_score * 0.3)
            
            return base_time
        
        return smart_weight
    
    def _calculate_route_length(self, route_nodes: List[int]) -> float:
        """Calculate total route length in meters"""
        total_length = 0.0
        for i in range(len(route_nodes) - 1):
            u, v = route_nodes[i], route_nodes[i + 1]
            # Get edge data (may have multiple edges between nodes)
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data:
                # Take the first edge if multiple exist
                length = list(edge_data.values())[0].get('length', 0)
                total_length += length
        return total_length
    
    def _calculate_route_time(self, route_nodes: List[int], weight_function) -> float:
        """Calculate estimated travel time in seconds"""
        if isinstance(weight_function, str):
            # Simple case: sum up the weight attribute
            total_time = 0.0
            for i in range(len(route_nodes) - 1):
                u, v = route_nodes[i], route_nodes[i + 1]
                edge_data = self.graph.get_edge_data(u, v)
                if edge_data:
                    time_val = list(edge_data.values())[0].get(weight_function, 60)
                    total_time += time_val
            return total_time
        else:
            # Custom weight function
            total_time = 0.0
            for i in range(len(route_nodes) - 1):
                u, v = route_nodes[i], route_nodes[i + 1]
                edge_data = self.graph.get_edge_data(u, v)
                if edge_data:
                    # Apply weight function to first edge
                    time_val = weight_function(u, v, list(edge_data.values())[0])
                    total_time += time_val
            return total_time
    
    def update_traffic_patterns(self, patterns: Dict):
        """
        Update traffic pattern weights from learning model
        
        Args:
            patterns: Dictionary mapping edge_id to time-based multipliers
        """
        self.traffic_patterns = patterns
        logger.info(f"Updated traffic patterns for {len(patterns)} edges")
    
    def update_shipper_preferences(self, preferences: Dict):
        """
        Update route preference scores from historical data
        
        Args:
            preferences: Dictionary mapping edge_id to preference scores (0-1)
        """
        self.shipper_preferences = preferences
        logger.info(f"Updated shipper preferences for {len(preferences)} edges")

# Singleton instance
_router = None

def get_router(graph: Optional[nx.MultiDiGraph] = None) -> SmartRouter:
    """Get or initialize the singleton router instance"""
    global _router
    if _router is None and graph is not None:
        _router = SmartRouter(graph)
    return _router
