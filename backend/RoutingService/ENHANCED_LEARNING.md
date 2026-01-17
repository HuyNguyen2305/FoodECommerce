# Enhanced Learning System for Single-Shop Routing

## Overview
This document describes the 4 focused enhancements added to the routing model's learning system, optimized for a single-shop setup.

## System Architecture

### Core Components
1. **Route Memory** (`route_memory.py`) - Core learning persistence
2. **Smart Router** (`smart_router.py`) - A* pathfinding with learning integration
3. **Dispatcher** (`dispatcher.py`) - Smart shipper assignment
4. **Context Utils** (`context_utils.py`) - Time-based context detection
5. **Learning API** (`app.py`) - Feedback endpoints
6. **Order Controller** (`orderController.js`) - Node.js feedback hook

---

## Enhancement 1: Delivery Zone Learning

### Purpose
Learn delivery time patterns from the shop to different customer zones (areas of the city).

### How It Works
- Customer locations are grouped into 100m x 100m grid zones using grid hashing
- Each zone tracks average delivery time using Exponential Moving Average (EMA, α=0.15)
- Times are context-aware (rush hours, weekday/weekend)

### MongoDB Collection
```javascript
delivery_zones {
  dest_zone: "106.7000_10.7800",  // Grid hash of customer zone
  context: "weekday_evening_rush", // Time context
  avg_time_seconds: 720,           // Learned average time
  sample_count: 15,                // Number of deliveries learned from
  last_updated: ISODate("...")
}
```

### Learning Method
```python
update_delivery_zone_pattern(customer_lat, customer_lon, actual_time_seconds, context)
```

### Usage in Smart Assignment
```python
learned_time = route_memory.get_delivery_zone_time(customer_lat, customer_lon)
if learned_time:
    delivery_eta = learned_time * shipper_multiplier
```

---

## Enhancement 2: Shipper Performance Tracking

### Purpose
Track how fast each shipper actually completes routes compared to estimates.

### How It Works
- Each shipper has a speed multiplier (default 1.0)
- Multiplier is learned from actual vs estimated times: `actual / estimated`
- Uses EMA to smooth out individual variations
- Multiplier < 1.0 = faster than estimate, > 1.0 = slower

### MongoDB Collection
```javascript
shipper_performance {
  shipper_id: "SH001",
  speed_multiplier: 0.85,  // This shipper is 15% faster than estimates
  delivery_count: 42,      // Total deliveries tracked
  last_updated: ISODate("...")
}
```

### Learning Method
```python
update_shipper_performance(shipper_id, estimated_time, actual_time)
```

### Usage in Smart Assignment
```python
shipper_multiplier = route_memory.get_shipper_multiplier(shipper_id)  # e.g., 0.85
pickup_eta = route_time * shipper_multiplier  # Apply to all route calculations
```

---

## Enhancement 3: Two-Leg Complete Journey Tracking

### Purpose
Learn complete delivery patterns from shipper starting location → shop → customer.

### How It Works
- Tracks full journey time from where shipper was when assigned
- Uses grid hashing for both shipper origin and customer destination
- Captures real-world patterns including traffic, parking, handoff time

### MongoDB Collection
```javascript
complete_journeys {
  origin_zone: "106.6950_10.7750",     // Shipper starting zone (grid hash)
  dest_zone: "106.7100_10.7850",       // Customer zone (grid hash)
  context: "weekday_lunch_rush",       // Time context
  avg_total_time_seconds: 1080,        // Learned total journey time
  sample_count: 8,                     // Deliveries tracked
  last_updated: ISODate("...")
}
```

### Learning Method
```python
update_complete_journey(shipper_lat, shipper_lon, customer_lat, customer_lon, total_time_seconds, context)
```

### Future Usage
Can be used to predict total delivery time when we know shipper's starting location, without calculating individual routes.

---

## Enhancement 4: Smart Assignment Algorithm

### Purpose
Assign orders to the shipper with the **lowest total predicted delivery time**, not just nearest to shop.

### How It Works

#### Old Algorithm (Distance-Based)
```python
1. Calculate route from each shipper → shop
2. Pick shipper with shortest distance
```

#### New Algorithm (Time-Based)
```python
1. For each available shipper:
   a. Calculate route: shipper → shop (pickup time)
   b. Get shipper's speed multiplier
   c. Apply multiplier to pickup time
   d. Calculate/lookup route: shop → customer (delivery time)
   e. Apply multiplier to delivery time
   f. Total time = pickup time + delivery time

2. Pick shipper with LOWEST total time
```

### Code Location
- **Dispatcher**: `find_nearest_shipper()` in `dispatcher.py`
- **Learning Integration**: Uses `get_shipper_multiplier()` and `get_delivery_zone_time()`

### Example Scenario
```
Scenario: Customer orders from shop at (10.7769, 106.7009)

Shipper A:
- Distance to shop: 2km
- Speed multiplier: 1.2 (20% slower)
- Pickup ETA: 5min * 1.2 = 6min
- Delivery ETA: 8min * 1.2 = 9.6min
- TOTAL: 15.6min

Shipper B:
- Distance to shop: 3km
- Speed multiplier: 0.8 (20% faster)
- Pickup ETA: 7min * 0.8 = 5.6min
- Delivery ETA: 8min * 0.8 = 6.4min
- TOTAL: 12min ← WINNER!

Old algorithm would pick Shipper A (closer)
New algorithm picks Shipper B (faster overall delivery)
```

---

## Learning Feedback Loop

### Trigger
When a delivery completes, the shipper mobile app updates order status to `delivered`.

### Flow
```
1. shipperMobile app → PUT /order/shipper/status/:orderId
   { shipper_status: 'delivered' }

2. orderController.js (Node.js backend)
   - Checks if status === 'delivered'
   - Extracts: shipper_id, shipper_location, shop_location, customer_location
   - Calculates actual delivery time
   
3. → POST http://localhost:5001/learning/record-delivery
   {
     order_id, shipper_id, shipper_location,
     shop_location, customer_location,
     assignment_time, delivery_time, estimated_time_seconds
   }

4. app.py (Python routing service)
   - Calls route_memory.update_delivery_zone_pattern()
   - Calls route_memory.update_shipper_performance()
   - Calls route_memory.update_complete_journey()
   - Calls router.record_actual_delivery() (existing route learning)

5. All learning data persists to MongoDB 'test' database
```

---

## Context Detection

### Time Contexts
```python
"weekday_morning"      # Mon-Fri 6am-9am
"weekday_morning_rush" # Mon-Fri 7am-9am (1.4x multiplier)
"weekday_lunch"        # Mon-Fri 11am-2pm
"weekday_lunch_rush"   # Mon-Fri 12pm-1pm (1.3x multiplier)
"weekday_afternoon"    # Mon-Fri 2pm-5pm
"weekday_evening"      # Mon-Fri 5pm-8pm
"weekday_evening_rush" # Mon-Fri 5pm-7pm (1.5x multiplier)
"weekday_night"        # Mon-Fri 8pm-6am
"weekend_morning"      # Sat-Sun 8am-12pm
"weekend_afternoon"    # Sat-Sun 12pm-6pm
"weekend_evening"      # Sat-Sun 6pm-10pm
"weekend_night"        # Sat-Sun 10pm-8am
```

### Rush Hour Multipliers
- **Morning rush (7-9am)**: 1.4x
- **Lunch rush (12-1pm)**: 1.3x
- **Evening rush (5-7pm)**: 1.5x

---

## MongoDB Collections Summary

| Collection | Purpose | Key Fields | Index |
|-----------|---------|-----------|-------|
| `route_memory` | Basic route learning | origin_zone, dest_zone, context | origin_dest_idx |
| `delivery_zones` | Shop→Customer zones | dest_zone, context, avg_time | dest_zone_idx |
| `shipper_performance` | Shipper speed tracking | shipper_id, speed_multiplier | shipper_id_idx |
| `complete_journeys` | Full journey patterns | origin_zone, dest_zone, context | journey_od_idx |
| `traffic_patterns` | Traffic conditions | zone, time_of_day | zone_time_idx |
| `interactions` | Learning interactions | timestamp, cache_hit | timestamp_idx |

---

## Configuration

### MongoDB Connection
```python
# backend/RoutingService/.env
MONGO_URI=mongodb+srv://cluster0.9vsew15.mongodb.net/test?retryWrites=true&w=majority
```

### Learning Parameters
```python
# route_memory.py
GRID_SIZE = 0.001  # 100m precision for location clustering
LEARNING_RATE = 0.15  # EMA alpha (15% weight to new data)
```

---

## Testing the System

### 1. Start Services
```bash
# Terminal 1: Node.js backend
cd backend
npm start

# Terminal 2: Python routing service
cd backend/RoutingService
python app.py
```

### 2. Create Test Order
```bash
POST /api/order/place
{
  "userId": "...",
  "items": [...],
  "address": {...}
}
```

### 3. Assign Shipper
```bash
POST /api/shipper/assign-order
{
  "shipper_id": "SH001",
  "order_id": "..."
}
```

### 4. Complete Delivery
```bash
PUT /api/order/shipper/status/:orderId
{
  "shipper_status": "delivered"
}
```

### 5. Check Learning
```bash
GET http://localhost:5001/learning/stats

Response:
{
  "total_routes_learned": 15,
  "cache_hits": 8,
  "cache_misses": 7,
  "cache_hit_rate": 53.3,
  "delivery_zones_learned": 12,
  "shippers_tracked": 5,
  "complete_journeys_tracked": 15
}
```

### 6. Verify MongoDB
```javascript
// MongoDB Compass
use test

db.delivery_zones.find()
db.shipper_performance.find()
db.complete_journeys.find()
```

---

## API Endpoints

### Learning Endpoints (Python - Port 5001)
- `POST /learning/record-delivery` - Record completed delivery
- `GET /learning/stats` - Get learning statistics
- `POST /learning/cleanup` - Clean old learning data

### Order Endpoints (Node.js - Port 5137)
- `PUT /api/order/shipper/status/:orderId` - Update shipper status (triggers learning)
- `GET /api/order/shipper/:shipperId` - Get shipper's orders

### Routing Endpoints (Python - Port 5001)
- `POST /route` - Calculate route with learning

---

## Key Improvements Over Basic System

| Feature | Before | After |
|---------|--------|-------|
| Assignment Logic | Nearest shipper to shop | Fastest total delivery time |
| Shipper Differences | All treated equally | Individual speed multipliers |
| Delivery Zones | Recalculate every time | Learn patterns, reuse knowledge |
| Journey Tracking | Only shop→customer | Complete shipper→shop→customer |
| Context Awareness | None | Rush hours, weekday/weekend |
| Learning Persistence | In-memory cache | MongoDB with EMA |

---

## Future Enhancements (Not Implemented)

1. **Shop Prep Time** - Track how long shop takes to prepare orders
2. **Expertise Tracking** - Learn which shippers are better for specific areas
3. **Weather Learning** - Adjust for rain, flooding
4. **Dynamic Pricing** - Suggest delivery fees based on predicted time
5. **Predictive Assignment** - Pre-assign shippers before order placement

---

## Logging & Debugging

### Enable Verbose Logging
```python
# route_memory.py
logger.info(f"📍 Zone learned: {dest_zone} → {avg_time:.0f}s (n={sample_count})")
logger.info(f"👤 Shipper {shipper_id} updated: {speed_multiplier:.2f}x (n={delivery_count})")
logger.info(f"🔄 Journey learned: {origin_zone}→{dest_zone} → {avg_total_time:.0f}s")
```

### Check Logs
```bash
# Python routing service logs
tail -f backend/RoutingService/app.log

# Node.js backend logs
# Look for: "✅ Delivery feedback sent to learning service"
```

---

## Single-Shop Optimization Benefits

1. **Fixed Shop Location** - All deliveries originate from same point
2. **Concentrated Learning** - All data feeds same origin, learns faster
3. **Simpler Patterns** - No multi-shop complexity
4. **Better Predictions** - More data per delivery zone
5. **Focused Shipper Analysis** - All shippers compared on same routes

---

## Performance Metrics to Track

1. **Prediction Accuracy** - How close are estimates to actual times?
2. **Cache Hit Rate** - % of routes served from learned patterns
3. **Assignment Quality** - Did we pick the fastest shipper?
4. **Learning Coverage** - % of delivery zones with learned data
5. **Shipper Consistency** - Stability of speed multipliers over time

---

## Maintenance

### Cleanup Old Data
```bash
POST http://localhost:5001/learning/cleanup
{
  "days_old": 90
}
```

### Reset Learning
```javascript
// MongoDB
db.delivery_zones.deleteMany({})
db.shipper_performance.deleteMany({})
db.complete_journeys.deleteMany({})
db.route_memory.deleteMany({})
```

---

## Summary

The enhanced learning system transforms the routing model from a simple A* pathfinder into an intelligent dispatcher that:
- **Learns** from every delivery
- **Predicts** accurate delivery times
- **Optimizes** shipper assignments
- **Adapts** to traffic patterns and shipper performance
- **Persists** knowledge for long-term improvement

All while remaining optimized for a single-shop food delivery operation in Ho Chi Minh City.
