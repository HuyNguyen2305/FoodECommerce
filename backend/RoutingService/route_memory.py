"""
Route Memory System - Learn from Historical Deliveries
======================================================
Implements route memoization with grid-based location hashing
"""
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from pymongo import MongoClient, ASCENDING
import os

logger = logging.getLogger(__name__)


class RouteMemory:
    """
    Manages route caching and learning from historical delivery data
    """
    
    def __init__(self, mongo_uri: str = None, db_name: str = None):
        """
        Initialize route memory system
        
        Args:
            mongo_uri: MongoDB connection string
            db_name: Database name (reads from DATABASE_NAME env var)
        """
        # MongoDB setup - same database as food recommendation model
        mongo_uri = mongo_uri or os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
        db_name = db_name or os.getenv('DATABASE_NAME', 'test')
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        
        # Collections
        self.route_memory = self.db.route_memory
        self.traffic_patterns = self.db.traffic_patterns
        self.delivery_zones = self.db.delivery_zones  # NEW: Zone learning from shop
        self.shipper_performance = self.db.shipper_performance  # NEW: Shipper speed tracking
        self.complete_journeys = self.db.complete_journeys  # NEW: Two-leg journey data
        
        # Grid precision (meters) - locations within this distance use same route
        self.grid_precision = 100  # 100 meters
        
        # Confidence thresholds
        self.min_samples_low = 3      # Start using cached route
        self.min_samples_medium = 10  # Moderate confidence
        self.min_samples_high = 25    # High confidence
        
        # Learning rate for exponential moving average
        self.learning_rate = 0.15  # Weight new data at 15%
        
        self._setup_indexes()
        logger.info("✅ Route Memory System initialized")
    
    def _setup_indexes(self):
        """Create MongoDB indexes for efficient lookups"""
        try:
            # Compound index for O-D pair lookups
            self.route_memory.create_index(
                [('origin_hash', ASCENDING), ('destination_hash', ASCENDING)],
                unique=True,
                name='od_pair_index'
            )
            
            # Index for cleanup queries
            self.route_memory.create_index('last_used', name='last_used_idx')
            self.route_memory.create_index('times_used', name='times_used_idx')
            
            # Delivery zones index
            self.delivery_zones.create_index('destination_hash', name='dest_zone_idx')
            
            # Shipper performance index
            self.shipper_performance.create_index('shipper_id', unique=True, name='shipper_id_idx')
            
            # Complete journeys compound index
            self.complete_journeys.create_index(
                [('shipper_zone_hash', ASCENDING), ('destination_hash', ASCENDING)],
                name='journey_od_idx'
            )
            
            logger.info("Route memory indexes created")
        except Exception as e:
            logger.warning(f"Index creation: {e}")
    
    def grid_hash(self, lat: float, lon: float, precision: int = None) -> str:
        """
        Create grid-based hash for location clustering
        
        Locations within grid_precision meters will have same hash
        
        Args:
            lat: Latitude
            lon: Longitude
            precision: Grid size in meters (default: self.grid_precision)
            
        Returns:
            Grid hash string like "107769_1067009"
        """
        precision = precision or self.grid_precision
        
        # Convert lat/lon to approximate meters at this latitude
        # At latitude ~10.77 (Ho Chi Minh), 1 degree lat ≈ 111,320 meters
        # 1 degree lon ≈ 109,000 meters (varies by latitude)
        meters_per_degree_lat = 111320
        meters_per_degree_lon = 109000 * math.cos(math.radians(lat))
        
        # Convert to grid coordinates
        grid_lat = int(lat * meters_per_degree_lat / precision)
        grid_lon = int(lon * meters_per_degree_lon / precision)
        
        return f"{grid_lat}_{grid_lon}"
    
    def get_od_pair_key(self, origin_lat: float, origin_lon: float,
                        dest_lat: float, dest_lon: float) -> Dict[str, str]:
        """
        Generate origin-destination pair keys
        
        Returns:
            Dict with 'origin_hash' and 'destination_hash'
        """
        return {
            'origin_hash': self.grid_hash(origin_lat, origin_lon),
            'destination_hash': self.grid_hash(dest_lat, dest_lon)
        }
    
    def lookup_route(self, origin_lat: float, origin_lon: float,
                     dest_lat: float, dest_lon: float,
                     context: str = None) -> Optional[Dict]:
        """
        Look up cached route for O-D pair
        
        Args:
            origin_lat, origin_lon: Start location
            dest_lat, dest_lon: End location
            context: Time context (e.g., "weekday_morning")
            
        Returns:
            Cached route data or None if not found or insufficient samples
        """
        try:
            od_key = self.get_od_pair_key(origin_lat, origin_lon, dest_lat, dest_lon)
            
            cached = self.route_memory.find_one(od_key)
            
            if not cached:
                return None
            
            # Check if we have enough samples to trust the cache
            if cached['times_used'] < self.min_samples_low:
                logger.debug(f"Insufficient samples ({cached['times_used']}), skipping cache")
                return None
            
            # Get context-specific timing if available
            if context and context in cached.get('time_patterns', {}):
                pattern = cached['time_patterns'][context]
                cached['estimated_time_seconds'] = pattern['avg_seconds']
                cached['confidence'] = self._calculate_confidence(cached['times_used'], pattern['samples'])
            else:
                # Use overall average
                cached['estimated_time_seconds'] = cached.get('avg_time_seconds', 0)
                cached['confidence'] = self._calculate_confidence(cached['times_used'], cached['times_used'])
            
            # Update last used timestamp
            self.route_memory.update_one(
                od_key,
                {'$set': {'last_used': datetime.now()}}
            )
            
            logger.info(f"📦 Cache HIT: {od_key['origin_hash']} → {od_key['destination_hash']} "
                       f"({cached['times_used']} uses, {cached['confidence']:.0%} confidence)")
            
            return cached
            
        except Exception as e:
            logger.error(f"Error looking up route: {e}")
            return None
    
    def save_route(self, origin_lat: float, origin_lon: float,
                   dest_lat: float, dest_lon: float,
                   route_data: Dict, estimated_time: float = None):
        """
        Save new route to memory
        
        Args:
            origin_lat, origin_lon: Start location
            dest_lat, dest_lon: End location
            route_data: Route information (coordinates, nodes, distance)
            estimated_time: Estimated time in seconds
        """
        try:
            od_key = self.get_od_pair_key(origin_lat, origin_lon, dest_lat, dest_lon)
            
            route_doc = {
                **od_key,
                'origin_coords': {'lat': origin_lat, 'lon': origin_lon},
                'destination_coords': {'lat': dest_lat, 'lon': dest_lon},
                'cached_route': {
                    'coordinates': route_data.get('coordinates', []),
                    'nodes': route_data.get('nodes', []),
                    'distance_meters': route_data.get('distance_meters', 0)
                },
                'avg_time_seconds': estimated_time or 0,
                'times_used': 1,
                'time_patterns': {},
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'last_updated': datetime.now()
            }
            
            self.route_memory.update_one(
                od_key,
                {'$setOnInsert': route_doc},
                upsert=True
            )
            
            logger.info(f"💾 Saved route: {od_key['origin_hash']} → {od_key['destination_hash']}")
            
        except Exception as e:
            logger.error(f"Error saving route: {e}")
    
    def update_performance(self, origin_lat: float, origin_lon: float,
                          dest_lat: float, dest_lon: float,
                          actual_time_seconds: float,
                          context: str = 'general',
                          estimated_time: float = None):
        """
        Update route performance with actual delivery data
        
        This is the LEARNING mechanism!
        
        Args:
            origin_lat, origin_lon: Start location
            dest_lat, dest_lon: End location
            actual_time_seconds: Actual delivery time
            context: Time context (e.g., "weekday_morning")
            estimated_time: Original estimate (for accuracy tracking)
        """
        try:
            od_key = self.get_od_pair_key(origin_lat, origin_lon, dest_lat, dest_lon)
            
            # Get existing data
            existing = self.route_memory.find_one(od_key)
            
            if not existing:
                logger.warning(f"No cached route found for update, skipping learning")
                return
            
            # Update overall average using exponential moving average
            old_avg = existing.get('avg_time_seconds', actual_time_seconds)
            new_avg = old_avg * (1 - self.learning_rate) + actual_time_seconds * self.learning_rate
            
            # Update context-specific pattern
            patterns = existing.get('time_patterns', {})
            
            if context not in patterns:
                patterns[context] = {
                    'avg_seconds': actual_time_seconds,
                    'samples': 1,
                    'min_seconds': actual_time_seconds,
                    'max_seconds': actual_time_seconds
                }
            else:
                old_pattern_avg = patterns[context]['avg_seconds']
                pattern_samples = patterns[context]['samples']
                
                # Exponential moving average for pattern
                patterns[context]['avg_seconds'] = (
                    old_pattern_avg * (1 - self.learning_rate) + 
                    actual_time_seconds * self.learning_rate
                )
                patterns[context]['samples'] = pattern_samples + 1
                patterns[context]['min_seconds'] = min(
                    patterns[context]['min_seconds'], actual_time_seconds
                )
                patterns[context]['max_seconds'] = max(
                    patterns[context]['max_seconds'], actual_time_seconds
                )
            
            # Calculate accuracy if estimate provided
            accuracy_delta = None
            if estimated_time:
                accuracy_delta = abs(estimated_time - actual_time_seconds) / actual_time_seconds
            
            # Update database
            update_data = {
                'avg_time_seconds': new_avg,
                'time_patterns': patterns,
                'last_updated': datetime.now(),
                '$inc': {'times_used': 1}
            }
            
            if accuracy_delta is not None:
                update_data['last_accuracy_delta'] = accuracy_delta
            
            self.route_memory.update_one(
                od_key,
                {'$set': update_data}
            )
            
            logger.info(f"📈 LEARNED: {od_key['origin_hash']} → {od_key['destination_hash']} "
                       f"| Context: {context} | Actual: {actual_time_seconds:.0f}s "
                       f"| New Avg: {new_avg:.0f}s | Uses: {existing['times_used'] + 1}")
            
        except Exception as e:
            logger.error(f"Error updating route performance: {e}")
    
    def update_delivery_zone_pattern(self, customer_lat: float, customer_lon: float,
                                     actual_time_seconds: float,
                                     context: str = 'general'):
        """
        Update delivery zone patterns from YOUR SHOP to customer zones
        
        Since shop location is fixed, focus learning on destination zones
        
        Args:
            customer_lat, customer_lon: Customer delivery location
            actual_time_seconds: Actual delivery time (shop → customer)
            context: Time context
        """
        try:
            # Get customer zone hash
            dest_hash = self.grid_hash(customer_lat, customer_lon)
            
            # Get existing zone data
            existing = self.delivery_zones.find_one({'destination_hash': dest_hash})
            
            if not existing:
                # Create new zone entry
                zone_doc = {
                    'destination_hash': dest_hash,
                    'destination_coords': {'lat': customer_lat, 'lon': customer_lon},
                    'avg_time_seconds': actual_time_seconds,
                    'time_patterns': {
                        context: {
                            'avg_seconds': actual_time_seconds,
                            'samples': 1,
                            'min_seconds': actual_time_seconds,
                            'max_seconds': actual_time_seconds
                        }
                    },
                    'times_delivered': 1,
                    'created_at': datetime.now(),
                    'last_updated': datetime.now()
                }
                
                self.delivery_zones.insert_one(zone_doc)
                logger.info(f"📍 New delivery zone: {dest_hash} | {actual_time_seconds:.0f}s")
            else:
                # Update existing zone
                old_avg = existing.get('avg_time_seconds', actual_time_seconds)
                new_avg = old_avg * (1 - self.learning_rate) + actual_time_seconds * self.learning_rate
                
                patterns = existing.get('time_patterns', {})
                
                if context not in patterns:
                    patterns[context] = {
                        'avg_seconds': actual_time_seconds,
                        'samples': 1,
                        'min_seconds': actual_time_seconds,
                        'max_seconds': actual_time_seconds
                    }
                else:
                    old_pattern = patterns[context]['avg_seconds']
                    patterns[context]['avg_seconds'] = (
                        old_pattern * (1 - self.learning_rate) + 
                        actual_time_seconds * self.learning_rate
                    )
                    patterns[context]['samples'] += 1
                    patterns[context]['min_seconds'] = min(
                        patterns[context]['min_seconds'], actual_time_seconds
                    )
                    patterns[context]['max_seconds'] = max(
                        patterns[context]['max_seconds'], actual_time_seconds
                    )
                
                self.delivery_zones.update_one(
                    {'destination_hash': dest_hash},
                    {
                        '$set': {
                            'avg_time_seconds': new_avg,
                            'time_patterns': patterns,
                            'last_updated': datetime.now()
                        },
                        '$inc': {'times_delivered': 1}
                    }
                )
                
                logger.info(f"📍 Zone learned: {dest_hash} | {context} | {new_avg:.0f}s avg | "
                           f"{existing['times_delivered'] + 1} deliveries")
        
        except Exception as e:
            logger.error(f"Error updating delivery zone: {e}")
    
    def update_shipper_performance(self, shipper_id: str,
                                   estimated_time: float,
                                   actual_time: float):
        """
        Track shipper performance - simple speed multiplier
        
        Args:
            shipper_id: Shipper identifier
            estimated_time: Predicted route time
            actual_time: Actual time taken
        """
        try:
            # Calculate performance ratio
            performance_ratio = actual_time / estimated_time if estimated_time > 0 else 1.0
            
            # Get existing performance
            existing = self.shipper_performance.find_one({'shipper_id': shipper_id})
            
            if not existing:
                # New shipper
                perf_doc = {
                    'shipper_id': shipper_id,
                    'speed_multiplier': performance_ratio,
                    'samples': 1,
                    'created_at': datetime.now(),
                    'last_updated': datetime.now()
                }
                self.shipper_performance.insert_one(perf_doc)
                logger.info(f"👤 New shipper: {shipper_id} | Speed: {performance_ratio:.2f}x")
            else:
                # Update existing
                old_multiplier = existing.get('speed_multiplier', 1.0)
                new_multiplier = (
                    old_multiplier * (1 - self.learning_rate) + 
                    performance_ratio * self.learning_rate
                )
                
                self.shipper_performance.update_one(
                    {'shipper_id': shipper_id},
                    {
                        '$set': {
                            'speed_multiplier': new_multiplier,
                            'last_updated': datetime.now()
                        },
                        '$inc': {'samples': 1}
                    }
                )
                
                logger.info(f"👤 Shipper updated: {shipper_id} | Speed: {new_multiplier:.2f}x | "
                           f"{existing['samples'] + 1} deliveries")
        
        except Exception as e:
            logger.error(f"Error updating shipper performance: {e}")
    
    def update_complete_journey(self, shipper_lat: float, shipper_lon: float,
                               customer_lat: float, customer_lon: float,
                               total_time_seconds: float,
                               context: str = 'general'):
        """
        Track complete two-leg journey: shipper → shop → customer
        
        Args:
            shipper_lat, shipper_lon: Shipper starting location
            customer_lat, customer_lon: Final delivery location
            total_time_seconds: Total time from assignment to delivery
            context: Time context
        """
        try:
            shipper_zone = self.grid_hash(shipper_lat, shipper_lon)
            customer_zone = self.grid_hash(customer_lat, customer_lon)
            
            journey_key = {
                'shipper_zone_hash': shipper_zone,
                'destination_hash': customer_zone
            }
            
            existing = self.complete_journeys.find_one(journey_key)
            
            if not existing:
                journey_doc = {
                    **journey_key,
                    'avg_total_time': total_time_seconds,
                    'time_patterns': {
                        context: {
                            'avg_seconds': total_time_seconds,
                            'samples': 1
                        }
                    },
                    'times_used': 1,
                    'created_at': datetime.now(),
                    'last_updated': datetime.now()
                }
                self.complete_journeys.insert_one(journey_doc)
                logger.info(f"🔄 New journey: {shipper_zone} → {customer_zone} | {total_time_seconds:.0f}s")
            else:
                old_avg = existing.get('avg_total_time', total_time_seconds)
                new_avg = old_avg * (1 - self.learning_rate) + total_time_seconds * self.learning_rate
                
                patterns = existing.get('time_patterns', {})
                if context not in patterns:
                    patterns[context] = {'avg_seconds': total_time_seconds, 'samples': 1}
                else:
                    old_pattern = patterns[context]['avg_seconds']
                    patterns[context]['avg_seconds'] = (
                        old_pattern * (1 - self.learning_rate) + 
                        total_time_seconds * self.learning_rate
                    )
                    patterns[context]['samples'] += 1
                
                self.complete_journeys.update_one(
                    journey_key,
                    {
                        '$set': {
                            'avg_total_time': new_avg,
                            'time_patterns': patterns,
                            'last_updated': datetime.now()
                        },
                        '$inc': {'times_used': 1}
                    }
                )
                
                logger.info(f"🔄 Journey learned: {shipper_zone} → {customer_zone} | "
                           f"{new_avg:.0f}s | {existing['times_used'] + 1} times")
        
        except Exception as e:
            logger.error(f"Error updating complete journey: {e}")
    
    def get_shipper_multiplier(self, shipper_id: str) -> float:
        """Get shipper speed multiplier (default 1.0)"""
        try:
            shipper = self.shipper_performance.find_one({'shipper_id': shipper_id})
            return shipper.get('speed_multiplier', 1.0) if shipper else 1.0
        except:
            return 1.0
    
    def get_delivery_zone_time(self, customer_lat: float, customer_lon: float,
                               context: str = None) -> Optional[float]:
        """Get learned time to delivery zone"""
        try:
            dest_hash = self.grid_hash(customer_lat, customer_lon)
            zone = self.delivery_zones.find_one({'destination_hash': dest_hash})
            
            if not zone or zone.get('times_delivered', 0) < 3:
                return None  # Not enough data
            
            if context and context in zone.get('time_patterns', {}):
                return zone['time_patterns'][context]['avg_seconds']
            
            return zone.get('avg_time_seconds')
        except:
            return None
    
    def _calculate_confidence(self, total_samples: int, context_samples: int) -> float:
        """
        Calculate confidence level for cached route
        
        Returns:
            Confidence score 0.0 to 1.0
        """
        if context_samples >= self.min_samples_high:
            return 0.95
        elif context_samples >= self.min_samples_medium:
            return 0.80
        elif context_samples >= self.min_samples_low:
            return 0.60
        else:
            return 0.30
    
    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        try:
            total_routes = self.route_memory.count_documents({})
            high_confidence = self.route_memory.count_documents({
                'times_used': {'$gte': self.min_samples_high}
            })
            medium_confidence = self.route_memory.count_documents({
                'times_used': {'$gte': self.min_samples_medium, '$lt': self.min_samples_high}
            })
            low_confidence = self.route_memory.count_documents({
                'times_used': {'$gte': self.min_samples_low, '$lt': self.min_samples_medium}
            })
            
            # Get most used routes
            top_routes = list(self.route_memory.find(
                {},
                {'origin_hash': 1, 'destination_hash': 1, 'times_used': 1, 'avg_time_seconds': 1}
            ).sort('times_used', -1).limit(10))
            
            return {
                'total_cached_routes': total_routes,
                'high_confidence_routes': high_confidence,
                'medium_confidence_routes': medium_confidence,
                'low_confidence_routes': low_confidence,
                'cache_hit_rate': 'tracked_per_request',
                'top_routes': top_routes
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_old_routes(self, days_unused: int = 30):
        """Remove routes that haven't been used recently"""
        try:
            cutoff = datetime.now() - timedelta(days=days_unused)
            result = self.route_memory.delete_many({
                'last_used': {'$lt': cutoff},
                'times_used': {'$lt': 5}  # Only remove if not well-established
            })
            logger.info(f"Cleaned up {result.deleted_count} unused routes")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up routes: {e}")
            return 0


# Singleton instance
_route_memory = None

def get_route_memory() -> RouteMemory:
    """Get singleton route memory instance"""
    global _route_memory
    if _route_memory is None:
        _route_memory = RouteMemory()
    return _route_memory
