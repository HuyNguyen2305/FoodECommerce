"""
OpenStreetMap Data Loader for Vietnam Road Networks
===================================================
Downloads and processes OSM data for routing in Ho Chi Minh City
"""
import osmnx as ox
import networkx as nx
import pickle
import os
import logging
from typing import Tuple, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OSMMapLoader:
    """Handles downloading and caching of OSM road network data"""
    
    def __init__(self, cache_dir='map_cache'):
        """Initialize map loader with cache directory"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.graph = None
        
        # Configure osmnx settings for better performance
        ox.settings.use_cache = True
        ox.settings.log_console = True
        
    def download_city_graph(self, 
                           city_name="Ho Chi Minh City, Vietnam",
                           network_type='drive',
                           simplify=True) -> nx.MultiDiGraph:
        """
        Download road network for a city from OpenStreetMap
        
        Args:
            city_name: Name of the city to download
            network_type: Type of network ('drive', 'walk', 'bike', 'all')
            simplify: Whether to simplify the graph (remove unnecessary nodes)
            
        Returns:
            NetworkX MultiDiGraph representing the road network
        """
        cache_file = os.path.join(self.cache_dir, f'{city_name.replace(" ", "_")}_{network_type}.pkl')
        
        # Try to load from cache first
        if os.path.exists(cache_file):
            logger.info(f"Loading cached map data from {cache_file}")
            try:
                with open(cache_file, 'rb') as f:
                    self.graph = pickle.load(f)
                logger.info(f"Loaded graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
                return self.graph
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}. Downloading fresh data...")
        
        # Download from OSM
        logger.info(f"Downloading OSM data for {city_name}...")
        try:
            # Download graph by city name
            self.graph = ox.graph_from_place(
                city_name,
                network_type=network_type,
                simplify=simplify
            )
            
            # Add edge speeds and travel times
            self.graph = ox.add_edge_speeds(self.graph)
            self.graph = ox.add_edge_travel_times(self.graph)
            
            logger.info(f"Downloaded graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
            
            # Save to cache
            with open(cache_file, 'wb') as f:
                pickle.dump(self.graph, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Cached map data to {cache_file}")
            
            return self.graph
            
        except Exception as e:
            logger.error(f"Failed to download map data: {e}")
            raise
    
    def download_bbox_graph(self, 
                           north: float, 
                           south: float, 
                           east: float, 
                           west: float,
                           network_type='drive') -> nx.MultiDiGraph:
        """
        Download road network for a bounding box area
        
        Args:
            north, south, east, west: Bounding box coordinates
            network_type: Type of network ('drive', 'walk', 'bike', 'all')
            
        Returns:
            NetworkX MultiDiGraph representing the road network
        """
        cache_file = os.path.join(
            self.cache_dir, 
            f'bbox_{north}_{south}_{east}_{west}_{network_type}.pkl'
        )
        
        # Try to load from cache
        if os.path.exists(cache_file):
            logger.info(f"Loading cached bbox map from {cache_file}")
            with open(cache_file, 'rb') as f:
                self.graph = pickle.load(f)
            return self.graph
        
        # Download from OSM
        logger.info(f"Downloading OSM data for bbox...")
        try:
            self.graph = ox.graph_from_bbox(
                north, south, east, west,
                network_type=network_type,
                simplify=True
            )
            
            # Add speeds and times
            self.graph = ox.add_edge_speeds(self.graph)
            self.graph = ox.add_edge_travel_times(self.graph)
            
            # Cache it
            with open(cache_file, 'wb') as f:
                pickle.dump(self.graph, f)
            
            logger.info(f"Downloaded bbox graph with {len(self.graph.nodes)} nodes")
            return self.graph
            
        except Exception as e:
            logger.error(f"Failed to download bbox: {e}")
            raise
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the loaded graph"""
        if self.graph is None:
            return {'error': 'No graph loaded'}
        
        return {
            'nodes': len(self.graph.nodes),
            'edges': len(self.graph.edges),
            'is_directed': self.graph.is_directed(),
            'is_multigraph': self.graph.is_multigraph(),
        }

# Singleton instance
_map_loader = None

def get_map_loader() -> OSMMapLoader:
    """Get the singleton map loader instance"""
    global _map_loader
    if _map_loader is None:
        _map_loader = OSMMapLoader()
    return _map_loader
