import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Alert, View, Text, ActivityIndicator, TouchableOpacity, Platform, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import MapView, { Marker, Polyline, UrlTile, PROVIDER_DEFAULT } from 'react-native-maps';
import * as Location from 'expo-location';
import { orderService, Order } from '../services/orderService';
import { authService } from '../services/auth';

// Routing service API endpoint
// Use 10.0.2.2 for Android emulator to access host machine's localhost
const ROUTING_SERVICE_URL = Platform.select({
  android: 'http://10.0.2.2:5001',
  ios: 'http://localhost:5001',
  default: 'http://localhost:5001',
});

interface OrderScreenProps {
  onLogout?: () => void;
}

const OrderScreen = ({ onLogout }: OrderScreenProps) => {
  const mapRef = useRef<MapView>(null);
  const [shipperProfile, setShipperProfile] = useState<any>(null);
  const [userLocation, setUserLocation] = useState<{lat: number, lng: number} | null>(null);
  const [assignedOrders, setAssignedOrders] = useState<Order[]>([]);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [routeCoordinates, setRouteCoordinates] = useState<Array<{latitude: number, longitude: number}>>([]);
  const [loading, setLoading] = useState(false);
  const [routeInfo, setRouteInfo] = useState<{distance: number, time: number} | null>(null);
  const [routeMode, setRouteMode] = useState<'to_shop' | 'to_customer'>('to_shop');

  // Get user's current location and load shipper profile
  useEffect(() => {
    loadShipperProfile();
    getCurrentLocation();
    loadAssignedOrders();
    // Start location tracking
    const locationSubscription = startLocationTracking();
    
    // Poll for new orders every 30 seconds
    const orderInterval = setInterval(loadAssignedOrders, 30000);
    
    return () => {
      locationSubscription?.then(sub => sub?.remove());
      clearInterval(orderInterval);
    };
  }, []);

  const loadShipperProfile = async () => {
    const profile = await authService.getProfile();
    setShipperProfile(profile);
  };

  const loadAssignedOrders = async () => {
    const result = await orderService.getMyOrders();
    if (result.success && result.orders) {
      setAssignedOrders(result.orders);
      
      // Set first active order if available
      const activeOrders = result.orders.filter(o => 
        o.shipper_status !== 'delivered' && o.shipper_status !== 'cancelled'
      );
      
      if (activeOrders.length > 0 && !activeOrder) {
        selectOrder(activeOrders[0]);
      }
    }
  };

  const selectOrder = (order: Order) => {
    setActiveOrder(order);
    
    // Determine route mode based on order status
    if (order.shipper_status === 'assigned' || order.shipper_status === 'en_route_to_shop') {
      setRouteMode('to_shop');
      if (userLocation) {
        calculateRoute(
          { lat: userLocation.lat, lng: userLocation.lng },
          { lat: order.shop_location.lat, lng: order.shop_location.lon }
        );
      }
    } else if (order.shipper_status === 'picked_up' || order.shipper_status === 'en_route_to_customer') {
      setRouteMode('to_customer');
      if (userLocation && order.customer_location) {
        calculateRoute(
          { lat: userLocation.lat, lng: userLocation.lng },
          { lat: order.customer_location.lat, lng: order.customer_location.lon }
        );
      }
    }
  };

  const getCurrentLocation = async () => {
    try {
      // Request location permissions
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        Alert.alert(
          'Location Permission Required',
          'Please enable location services to show your current position on the map.',
          [{ text: 'OK' }]
        );
        return;
      }

      // Get current position
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      setUserLocation({
        lat: location.coords.latitude,
        lng: location.coords.longitude,
      });
      
      console.log('User location:', location.coords);
    } catch (error) {
      console.error('Error getting location:', error);
      Alert.alert('Location Error', 'Unable to get your current location. Using default location.');
      // Set default location for testing
      setUserLocation({ lat: 10.7769, lng: 106.7009 });
    }
  };
  
  const startLocationTracking = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return null;
      
      // Track location every 10 seconds
      return await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 10000, // 10 seconds
          distanceInterval: 10, // 10 meters
        },
        (location) => {
          setUserLocation({
            lat: location.coords.latitude,
            lng: location.coords.longitude,
          });
          console.log('Location update:', location.coords);
        }
      );
    } catch (error) {
      console.error('Location tracking error:', error);
      return null;
    }
  };
  
  const calculateRoute = async (from: {lat: number, lng: number}, to: {lat: number, lng: number}) => {
    setLoading(true);
    try {
      console.log(`🚗 Calculating route using: ${ROUTING_SERVICE_URL}`);
      const response = await fetch(`${ROUTING_SERVICE_URL}/route/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start: { lat: from.lat, lon: from.lng },
          end: { lat: to.lat, lon: to.lng },
          use_smart_routing: false, // Set to true once pattern learning is implemented
        }),
      });
      
      const data = await response.json();
      
      if (data.success && data.route) {
        // Convert coordinates from [lat, lon] to {latitude, longitude}
        const coords = data.route.coordinates.map((coord: number[]) => ({
          latitude: coord[0],
          longitude: coord[1],
        }));
        setRouteCoordinates(coords);
        setRouteInfo({
          distance: data.route.distance_meters,
          time: data.route.estimated_time_seconds,
        });
        
        console.log(`✅ Route calculated: ${data.route.distance_meters}m, ${data.route.estimated_time_seconds}s`);
      } else {
        Alert.alert('Route Error', data.error || 'Failed to calculate route');
      }
    } catch (error) {
      console.error('Route calculation error:', error);
      Alert.alert(
        'Network Error', 
        `Unable to connect to routing service at ${ROUTING_SERVICE_URL}\n\nMake sure the Python routing service is running on port 5001.`
      );
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    // Update route when user location changes
    if (activeOrder && userLocation) {
      if (routeMode === 'to_shop') {
        calculateRoute(
          { lat: userLocation.lat, lng: userLocation.lng },
          { lat: activeOrder.shop_location.lat, lng: activeOrder.shop_location.lon }
        );
      } else if (routeMode === 'to_customer' && activeOrder.customer_location) {
        calculateRoute(
          { lat: userLocation.lat, lng: userLocation.lng },
          { lat: activeOrder.customer_location.lat, lng: activeOrder.customer_location.lon }
        );
      }
    }
  }, [userLocation]);
  
  const handlePickup = async () => {
    if (!activeOrder) return;
    
    const result = await orderService.markPickedUp(activeOrder._id);
    if (result.success) {
      Alert.alert('Success', 'Order picked up! Now heading to customer.');
      setRouteMode('to_customer');
      loadAssignedOrders(); // Refresh orders
    } else {
      Alert.alert('Error', result.message || 'Failed to update status');
    }
  };

  const handleDelivery = async () => {
    if (!activeOrder) return;
    
    const result = await orderService.markDelivered(activeOrder._id);
    if (result.success) {
      Alert.alert('Success', 'Order delivered successfully!');
      setActiveOrder(null);
      setRouteCoordinates([]);
      loadAssignedOrders(); // Refresh to get next order
    } else {
      Alert.alert('Error', result.message || 'Failed to complete delivery');
    }
  };

  const handleAcceptOrder = async () => {
    if (!activeOrder) return;
    
    const result = await orderService.acceptOrder(activeOrder._id);
    if (result.success) {
      Alert.alert('Success', 'Order accepted! Heading to shop.');
      loadAssignedOrders(); // Refresh orders
    } else {
      Alert.alert('Error', result.message || 'Failed to accept order');
    }
  };
  
  const recalculateRoute = () => {
    if (activeOrder && userLocation) {
      if (routeMode === 'to_shop') {
        calculateRoute(
          userLocation,
          { lat: activeOrder.shop_location.lat, lng: activeOrder.shop_location.lon }
        );
      } else if (routeMode === 'to_customer' && activeOrder.customer_location) {
        calculateRoute(
          userLocation,
          { lat: activeOrder.customer_location.lat, lng: activeOrder.customer_location.lon }
        );
      }
    }
  };

  const zoomIn = () => {
    mapRef.current?.getCamera().then(camera => {
      if (camera.zoom) {
        mapRef.current?.animateCamera({ zoom: camera.zoom + 1 }, { duration: 300 });
      }
    });
  };

  const zoomOut = () => {
    mapRef.current?.getCamera().then(camera => {
      if (camera.zoom) {
        mapRef.current?.animateCamera({ zoom: camera.zoom - 1 }, { duration: 300 });
      }
    });
  };
  
  const initialRegion = userLocation ? {
    latitude: userLocation.lat,
    longitude: userLocation.lng,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  } : activeOrder ? {
    latitude: activeOrder.shop_location.lat,
    longitude: activeOrder.shop_location.lon,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  } : {
    latitude: 10.7769,
    longitude: 106.7009,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Shipper Profile Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View>
            {shipperProfile && (
              <>
                <Text style={styles.headerTitle}>{shipperProfile.name}</Text>
                <Text style={styles.headerSubtitle}>ID: {shipperProfile.shipper_id}</Text>
              </>
            )}
          </View>
          {onLogout && (
            <TouchableOpacity onPress={onLogout} style={styles.logoutButton}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          )}
        </View>
        
        {activeOrder && (
          <View style={styles.orderInfoContainer}>
            <Text style={styles.orderInfoTitle}>
              {routeMode === 'to_shop' ? '📦 Going to Shop' : '🏠 Delivering to Customer'}
            </Text>
            <Text style={styles.orderStatus}>Status: {activeOrder.shipper_status.replace(/_/g, ' ').toUpperCase()}</Text>
            {routeInfo && (
              <View style={styles.routeInfoContainer}>
                <Text style={styles.routeInfoText}>
                  {(routeInfo.distance / 1000).toFixed(2)} km
                </Text>
                <Text style={styles.routeInfoText}>
                  {Math.round(routeInfo.time / 60)} min
                </Text>
              </View>
            )}
          </View>
        )}
        
        {!activeOrder && (
          <View style={styles.noOrderContainer}>
            <Text style={styles.noOrderText}>
              {assignedOrders.length === 0 ? 'No orders assigned' : 'All orders completed'}
            </Text>
            {/* Test Route Button */}
            {userLocation && (
              <TouchableOpacity 
                style={styles.testRouteButton} 
                onPress={() => {
                  // Test route from current location to a sample shop
                  const testShop = { lat: 10.7769, lng: 106.7009 }; // Sample shop location
                  calculateRoute(userLocation, testShop);
                  Alert.alert('Test Route', 'Calculating route from your location to sample shop...');
                }}
              >
                <Text style={styles.testRouteButtonText}>Test Route (Current Location → Shop)</Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      </View>
      
      {/* Map with OpenStreetMap tiles */}
      <MapView
        ref={mapRef}
        style={styles.map}
        initialRegion={initialRegion}
        showsUserLocation={true}
        showsMyLocationButton={true}
        followsUserLocation={true}
      >
        {/* Use Carto OSM tiles (free, no restrictions for apps) */}
        <UrlTile
          urlTemplate="https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
          maximumZ={19}
          flipY={false}
        />
        
        {/* Shop Marker */}
        {activeOrder && (
          <Marker
            coordinate={{
              latitude: activeOrder.shop_location.lat,
              longitude: activeOrder.shop_location.lon,
            }}
            title="Shop - Pickup"
            description="Restaurant Location"
            pinColor="blue"
          />
        )}
        
        {/* Customer Marker */}
        {activeOrder && activeOrder.customer_location && (
          <Marker
            coordinate={{
              latitude: activeOrder.customer_location.lat,
              longitude: activeOrder.customer_location.lon,
            }}
            title="Customer"
            description="Delivery Address"
            pinColor="red"
          />
        )}
        
        {/* Route Polyline from A* algorithm */}
        {routeCoordinates.length > 0 && (
          <Polyline
            coordinates={routeCoordinates}
            strokeColor="#4285F4"
            strokeWidth={5}
            lineCap="round"
            lineJoin="round"
            geodesic={true}
          />
        )}
      </MapView>
      
      {/* Loading Overlay */}
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#4285F4" />
          <Text style={styles.loadingText}>Calculating route...</Text>
        </View>
      )}
      
      {/* Zoom Controls */}
      <View style={styles.zoomControls}>
        <TouchableOpacity style={styles.zoomButton} onPress={zoomIn}>
          <Text style={styles.zoomButtonText}>+</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.zoomButton} onPress={zoomOut}>
          <Text style={styles.zoomButtonText}>−</Text>
        </TouchableOpacity>
      </View>

      {/* Action Buttons */}
      {activeOrder && (
        <View style={styles.actionButtonsContainer}>
          {activeOrder.shipper_status === 'assigned' && (
            <TouchableOpacity style={styles.acceptButton} onPress={handleAcceptOrder}>
              <Text style={styles.actionButtonText}>Accept Order</Text>
            </TouchableOpacity>
          )}
          
          {activeOrder.shipper_status === 'en_route_to_shop' && (
            <TouchableOpacity style={styles.pickupButton} onPress={handlePickup}>
              <Text style={styles.actionButtonText}>Picked Up</Text>
            </TouchableOpacity>
          )}
          
          {(activeOrder.shipper_status === 'picked_up' || activeOrder.shipper_status === 'en_route_to_customer') && (
            <TouchableOpacity style={styles.deliveryButton} onPress={handleDelivery}>
              <Text style={styles.actionButtonText}>Complete Delivery</Text>
            </TouchableOpacity>
          )}
          
          <TouchableOpacity style={styles.recalculateButton} onPress={recalculateRoute} disabled={loading}>
            <Text style={styles.recalculateButtonText}>Recalculate Route</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    padding: 16,
    backgroundColor: '#4285F4',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#fff',
    marginTop: 4,
    opacity: 0.9,
  },
  logoutButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  logoutText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  orderInfoContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.3)',
  },
  orderInfoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  orderStatus: {
    fontSize: 14,
    color: '#fff',
    opacity: 0.9,
    marginBottom: 8,
  },
  noOrderContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.3)',
  },
  noOrderText: {
    fontSize: 16,
    color: '#fff',
    opacity: 0.9,
    textAlign: 'center',
    marginBottom: 12,
  },
  testRouteButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    marginTop: 8,
  },
  testRouteButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  routeInfoContainer: {
    flexDirection: 'row',
    gap: 16,
  },
  routeInfoText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  map: {
    flex: 1,
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  zoomControls: {
    position: 'absolute',
    right: 16,
    top: '50%',
    marginTop: -50,
    gap: 8,
  },
  zoomButton: {
    width: 44,
    height: 44,
    backgroundColor: '#fff',
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  zoomButtonText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  actionButtonsContainer: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    gap: 10,
  },
  acceptButton: {
    backgroundColor: '#34A853',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  pickupButton: {
    backgroundColor: '#FBBC04',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  deliveryButton: {
    backgroundColor: '#EA4335',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  recalculateButton: {
    backgroundColor: '#4285F4',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  recalculateButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default OrderScreen;
