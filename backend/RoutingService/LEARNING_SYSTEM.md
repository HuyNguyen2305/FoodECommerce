# Route Learning System Documentation

## Overview
The routing service now includes a complete learning system that improves route predictions based on actual delivery performance.

## How It Works

### 1. Route Memoization
- **Grid-based hashing**: Locations within 100m are grouped together
- **O-D Pair Caching**: Frequently used origin-destination pairs are stored in MongoDB
- **Context-aware**: Separate patterns for different times (morning, lunch, evening, etc.)

### 2. Learning Flow

```
Order Assigned → Route Calculated → Shipper Delivers
                      ↓                      ↓
                 Save to Memory      Update Performance
                      ↓                      ↓
              Next Similar Route ← Apply Learned Time
```

**Step by Step:**

1. **Route Request**: Check if route has been used before
   - If cached with 3+ samples → Use cached route
   - If new → Calculate with A* algorithm and save

2. **Delivery Completion**: When shipper_status → 'delivered'
   - Node.js sends feedback to Python service
   - Actual time vs estimated time is recorded
   - Pattern statistics updated using exponential moving average

3. **Future Predictions**: Apply learned patterns
   - Context multipliers (rush hour, time of day)
   - Historical averages for that specific route
   - Confidence-based weighting

### 3. Context Detection

Time patterns tracked:
- `weekday_morning` (7-11 AM)
- `weekday_lunch` (11-2 PM)
- `weekday_afternoon` (2-5 PM)
- `weekday_evening` (5-10 PM)
- `weekday_night` (10 PM-7 AM)
- `weekend_morning`, `weekend_lunch`, etc.
- `holiday_*` patterns

Traffic multipliers:
- Morning rush (7-9 AM): 1.4x slower
- Lunch rush (11-2 PM): 1.3x slower
- Evening rush (5-8 PM): 1.5x slower (worst!)
- Late night (10 PM-5 AM): 0.75x faster
- Weekend: 0.85x faster baseline
- Rain: 1.3x slower (expandable)

## MongoDB Collections

### route_memory
Stores cached routes with performance history:
```javascript
{
  origin_hash: "107769_1067009",
  destination_hash: "107829_1066958",
  origin_coords: {lat: 10.7769, lon: 106.7009},
  destination_coords: {lat: 10.7829, lon: 106.6958},
  
  cached_route: {
    coordinates: [[lat, lon], ...],
    nodes: [node_ids, ...],
    distance_meters: 3200
  },
  
  avg_time_seconds: 720,
  times_used: 45,
  
  time_patterns: {
    "weekday_morning": {
      avg_seconds: 840,
      samples: 12,
      min_seconds: 660,
      max_seconds: 1020
    },
    "weekday_evening": {
      avg_seconds: 1080,
      samples: 20,
      min_seconds: 900,
      max_seconds: 1320
    }
  },
  
  last_accuracy_delta: 0.12,
  created_at: ISODate(),
  last_used: ISODate(),
  last_updated: ISODate()
}
```

## API Endpoints

### Learning Endpoints (Python - Port 5001)

**POST /learning/record-delivery**
Called by Node.js when delivery completes
```json
{
  "order_id": "123",
  "shop_location": {"lat": 10.7769, "lon": 106.7009},
  "customer_location": {"lat": 10.7829, "lon": 106.6958},
  "assignment_time": "2026-01-17T10:00:00Z",
  "delivery_time": "2026-01-17T10:15:00Z",
  "estimated_time_seconds": 720
}
```

**GET /learning/stats**
View learning performance metrics
```json
{
  "success": true,
  "statistics": {
    "cache_hit_rate": 0.67,
    "cache_hits": 234,
    "cache_misses": 116,
    "total_cached_routes": 89,
    "high_confidence_routes": 23,
    "medium_confidence_routes": 34,
    "low_confidence_routes": 32
  }
}
```

**POST /learning/cleanup**
Clean up old unused routes
```json
{
  "days_unused": 30
}
```

## Confidence Levels

Routes are used based on confidence:
- **< 3 samples**: Don't use cache, calculate fresh
- **3-9 samples**: Low confidence (60%) - use cached route
- **10-24 samples**: Medium confidence (80%) - trusted
- **25+ samples**: High confidence (95%) - highly trusted

## Learning Rate

Uses exponential moving average (EMA) with α = 0.15:
```
new_avg = old_avg × 0.85 + new_data × 0.15
```

This gives recent data 15% weight while preserving 85% of historical pattern.

## Performance Benefits

### Speed Improvements
- Fresh A* calculation: 200-500ms
- Cached lookup: 5-10ms
- **~40x faster for cached routes**

### Accuracy Improvements
- OSM data: Based on speed limits (often outdated)
- Learned data: Based on YOUR actual deliveries
- Context-aware: Rush hour vs late night patterns

### Example Improvement
```
Route: McDonald's → Residential Area
- OSM Prediction: 15 minutes (fixed)
- Initial Learning: 12 minutes average
- After 50 deliveries:
  - Weekday morning: 14 minutes
  - Weekday evening: 18 minutes (rush hour!)
  - Weekend: 10 minutes
  - Late night: 8 minutes
```

## Integration Points

### Node.js → Python
1. **Order Assignment**: Calculate route (may use cache)
2. **Delivery Complete**: Send feedback for learning

### Python Components
1. **route_memory.py**: Manages caching and learning
2. **context_utils.py**: Time/weather context detection
3. **smart_router.py**: Route calculation with learning
4. **app.py**: Flask API endpoints

## Monitoring

Check learning performance:
```bash
curl http://localhost:5001/learning/stats
```

Watch logs for learning activity:
- `📦 Cache HIT`: Route served from memory
- `📈 LEARNED`: Performance data recorded
- `💾 Saved route`: New route added to memory

## Environment Variables

```bash
MONGODB_URL=mongodb://localhost:27017/
DATABASE_NAME=food-delivery
ROUTING_SERVICE_URL=http://localhost:5001  # Node.js needs this
```

## Future Enhancements

Potential improvements:
1. **GPS Tracking**: Learn actual paths shippers take (not just O-D pairs)
2. **Weather API**: Real-time rain/traffic integration
3. **Special Events**: Learn from concerts, festivals, holidays
4. **Shipper Behavior**: Individual shipper speed patterns
5. **Real-time Traffic**: Integrate Google Maps Traffic API
6. **Edge-based Learning**: Learn specific road segment speeds

## Testing the System

1. **Start services**:
   ```bash
   # Terminal 1: Node.js backend
   cd backend
   npm start
   
   # Terminal 2: Routing service
   cd backend/RoutingService
   python app.py
   ```

2. **Create test order** with shipper assignment

3. **Complete delivery** (change status to 'delivered')

4. **Check logs** for learning activity:
   ```
   ✅ Delivery feedback sent to learning service for order 123
   📈 LEARNED: 107769_1067009 → 107829_1066958 | Context: weekday_morning
   ```

5. **Request same route again** - should see cache hit!

## Success Metrics

Track these to measure learning effectiveness:
- Cache hit rate (target: >60% after 100 orders)
- Prediction accuracy (target: within 20% of actual)
- Number of high-confidence routes (growing over time)
- Average calculation time (decreasing as cache grows)

---

**The system is now ACTIVELY LEARNING from every delivery! 🚀**
