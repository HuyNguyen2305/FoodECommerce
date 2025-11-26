# Shipper Assignment Architecture

## Overview
The system now uses **server-side Dijkstra algorithm** to assign the nearest available shipper to each order, instead of shippers manually selecting routes.

---

## Flow Diagram

```
Customer Places Order
         ↓
    Order Created
    (status: pending)
         ↓
Backend Dispatcher Activates
         ↓
Dijkstra Algorithm Runs
(finds nearest shipper)
         ↓
Order Assigned to Shipper
(shipper_status: assigned)
         ↓
📱 Shipper Receives Notification
         ↓
Shipper Accepts Order
(shipper_status: en_route_to_shop)
         ↓
Route Displayed: Shipper → Shop
         ↓
Shipper Arrives at Shop
         ↓
Shipper Clicks "Picked Up"
(shipper_status: picked_up)
         ↓
Route Switches: Shop → Customer
         ↓
Shipper Arrives at Customer
         ↓
Shipper Clicks "Complete Delivery"
(shipper_status: delivered)
         ↓
Order Completed ✅
```

---

## Database Schema

### Order Model (Updated)
```javascript
{
  userId: String,
  items: Array,
  amount: Number,
  address: Object,
  status: String, // "Food Processing", "Out for delivery", "Delivered"
  payment: Boolean,
  
  // NEW: Shipper Assignment Fields
  assigned_shipper: ObjectId, // Reference to shipper
  shipper_status: String, // pending → assigned → en_route_to_shop → picked_up → en_route_to_customer → delivered
  assignment_time: Date,
  pickup_time: Date,
  delivery_time: Date,
  
  // NEW: Location Data
  shop_location: { lat: Number, lon: Number },
  customer_location: { lat: Number, lon: Number },
  estimated_distance_meters: Number,
  estimated_time_seconds: Number,
}
```

### Shipper Model
```javascript
{
  shipper_id: String, // SHIP0001, SHIP0002...
  name: String,
  email: String,
  phone: String,
  password: String, // Hashed
  current_location: { lat: Number, lon: Number },
  status: String, // available, busy, offline
  current_order: ObjectId,
  rating: Number,
  total_deliveries: Number,
}
```

---

## Backend API Endpoints

### Shipper Authentication
- `POST /api/shipper/register` - Register new shipper
- `POST /api/shipper/login` - Login (sets status to 'available')
- `GET /api/shipper/profile` - Get shipper profile (protected)
- `POST /api/shipper/update-location` - Update GPS coordinates (protected)
- `POST /api/shipper/update-status` - Change availability status (protected)

### Order Management (Shipper)
- `GET /api/order/shipper/:shipperId` - Get all assigned orders (protected)
- `PUT /api/order/shipper/status/:orderId` - Update delivery status (protected)
- `GET /api/order/:orderId` - Get order details (protected)

### Dispatcher Service (Python Flask)
- `GET /dispatch/shippers` - Get all available shippers with locations
- `POST /dispatch/find-nearest` - Find nearest shipper to a location using Dijkstra
- `POST /dispatch/assign` - Assign order to nearest shipper

---

## Mobile App (shipperMobile)

### Services

#### authService.ts
```typescript
login(email, password) → JWT token
register(name, email, phone, password) → account creation
logout() → clear session
getProfile() → shipper details
```

#### orderService.ts
```typescript
getMyOrders() → fetch assigned orders
updateOrderStatus(orderId, status) → update progress
markPickedUp(orderId) → picked up from shop
markDelivered(orderId) → delivered to customer
acceptOrder(orderId) → accept assignment
```

### OrderScreen Flow

1. **On Login**: Shipper sees their profile (name, ID, rating)
2. **Order Assignment**: Backend assigns order via Dijkstra
3. **Display Order**: Shows order details and route to shop
4. **Accept Order**: Shipper clicks "Accept Order"
   - Status: `assigned` → `en_route_to_shop`
   - Route: Shipper location → Shop location
5. **Arrive at Shop**: Shipper clicks "Picked Up"
   - Status: `en_route_to_shop` → `picked_up`
   - Route switches: Shop location → Customer location
6. **Arrive at Customer**: Shipper clicks "Complete Delivery"
   - Status: `picked_up` → `delivered`
   - Order completed, ready for next assignment

---

## Routing Algorithm

### A* Algorithm (Pathfinding)
- Used by Python Flask service (`RoutingService/app.py`)
- Calculates optimal route between two points
- Uses OpenStreetMap data (HCM City cached: 146,089 nodes)
- Returns: route coordinates, distance (meters), time (seconds)

### Dijkstra Algorithm (Nearest Shipper)
- Used by Dispatcher (`RoutingService/dispatcher.py`)
- Finds nearest available shipper to shop location
- Filters shippers within 10km radius
- Sorts by estimated time arrival (ETA)
- Assigns best match automatically

---

## Status Flow

### Order Statuses (Main)
- `Food Processing` - Restaurant preparing food
- `Out for delivery` - Shipper on the way
- `Delivered` - Customer received

### Shipper Statuses (Detailed)
1. **pending** - Order created, no shipper assigned
2. **assigned** - Dispatcher assigned shipper, awaiting acceptance
3. **en_route_to_shop** - Shipper accepted, heading to restaurant
4. **picked_up** - Shipper collected food from restaurant
5. **en_route_to_customer** - Shipper heading to customer
6. **delivered** - Order successfully delivered
7. **cancelled** - Order cancelled

---

## Key Changes

### ❌ OLD System
- Shipper logs in → sees random route to shop
- No assignment logic
- Manual order selection

### ✅ NEW System
- Customer places order → Backend finds nearest shipper
- Dijkstra algorithm assigns automatically
- Shipper receives notification on device
- Route switches: Shipper→Shop, then Shop→Customer
- Real-time status updates

---

## Next Steps

1. ✅ Update order model with shipper fields
2. ✅ Create order service for mobile app
3. ✅ Update OrderScreen to show assigned orders
4. ✅ Add status buttons (Accept, Picked Up, Delivered)
5. ⏳ Implement push notifications for order assignments
6. ⏳ Add background GPS tracking (locationService.ts)
7. ⏳ Create OrderListScreen for multiple orders
8. ⏳ Integrate dispatcher with order placement flow
9. ⏳ Test complete flow: Customer order → Shipper delivery

---

## Testing

### Test Credentials
- Email: `ship0001@shipper.local` through `ship0020@shipper.local`
- Password: `shipper123`

### Test Flow
1. Start backend: `npm run server` (port 5137)
2. Start routing service: `python app.py` (port 5001)
3. Open shipperMobile in Android emulator
4. Login with test credentials
5. Backend assigns order (manually trigger or wait for customer order)
6. Shipper sees order with route to shop
7. Test status transitions

---

## Architecture Benefits

1. **Automatic Assignment** - No manual shipper selection
2. **Optimal Routing** - Dijkstra finds nearest available shipper
3. **Real-time Updates** - GPS tracking and status updates
4. **Scalable** - Supports multiple shippers and orders
5. **Efficient** - Reduces delivery time and distance
6. **User-owned Algorithms** - A* and Dijkstra fully customizable

