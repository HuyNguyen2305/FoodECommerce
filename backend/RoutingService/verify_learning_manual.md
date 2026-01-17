# Manual Learning Verification Guide

This guide shows you how to manually verify that the routing model is learning.

## Quick Automated Test

Run the automated test script:

```bash
cd backend/RoutingService
python test_learning.py
```

This will:
- ✅ Check MongoDB connection
- ✅ Verify API endpoints
- ✅ Simulate deliveries
- ✅ Verify learning occurred
- ✅ Show before/after comparisons

---

## Manual Verification Steps

### 1. Check MongoDB Collections (Before Any Deliveries)

Open **MongoDB Compass** and connect to your cluster:
```
mongodb+srv://cluster0.9vsew15.mongodb.net/test
```

Check these collections - they should be **empty or have very few documents**:
- `delivery_zones`
- `shipper_performance`
- `complete_journeys`
- `route_memory`

**Take a screenshot or note the counts!**

---

### 2. Complete a Real Delivery

#### A. Create an Order (Frontend/Admin)
1. Go to your frontend
2. Place an order as a customer
3. Note the order ID

#### B. Assign a Shipper (Admin Panel or Postman)
```bash
POST http://localhost:5137/api/shipper/assign-order
Content-Type: application/json

{
  "shipper_id": "SH001",
  "order_id": "YOUR_ORDER_ID"
}
```

#### C. Mark as Delivered (Shipper Mobile App or Postman)
```bash
PUT http://localhost:5137/api/order/shipper/status/YOUR_ORDER_ID
Content-Type: application/json

{
  "shipper_status": "delivered"
}
```

---

### 3. Check if Learning Occurred

#### Option A: Check MongoDB (Visual Proof)

Go back to **MongoDB Compass** and refresh the collections:

**delivery_zones collection:**
```javascript
{
  dest_zone: "106.695_10.783",
  context: "weekday_afternoon",
  avg_time_seconds: 720,
  sample_count: 1,
  last_updated: ISODate("2026-01-17T...")
}
```
✅ **If you see a new document, delivery zone learning worked!**

**shipper_performance collection:**
```javascript
{
  shipper_id: "SH001",
  speed_multiplier: 1.05,
  delivery_count: 1,
  last_updated: ISODate("2026-01-17T...")
}
```
✅ **If you see your shipper, performance tracking worked!**

**complete_journeys collection:**
```javascript
{
  origin_zone: "106.700_10.770",
  dest_zone: "106.695_10.783",
  context: "weekday_afternoon",
  avg_total_time_seconds: 900,
  sample_count: 1,
  last_updated: ISODate("2026-01-17T...")
}
```
✅ **If you see a journey, complete journey tracking worked!**

#### Option B: Check Learning Stats API

```bash
GET http://localhost:5001/learning/stats
```

Response BEFORE any deliveries:
```json
{
  "total_routes_learned": 0,
  "cache_hits": 0,
  "cache_misses": 0,
  "cache_hit_rate": 0
}
```

Response AFTER a delivery:
```json
{
  "total_routes_learned": 1,
  "cache_hits": 0,
  "cache_misses": 1,
  "cache_hit_rate": 0,
  "delivery_zones_learned": 1,
  "shippers_tracked": 1,
  "complete_journeys_tracked": 1
}
```
✅ **Numbers increased = learning worked!**

---

### 4. Verify Learning is Actually Used

#### Test: Same Route Twice

1. **First delivery** to address A
   - Check cache_hit_rate: should be 0% (no prior knowledge)
   
2. **Second delivery** to same address A
   - Check cache_hit_rate: should be > 0% (using learned pattern!)

**How to verify:**
```bash
GET http://localhost:5001/learning/stats
```

Look at `cache_hit_rate`:
- After 1st delivery: 0%
- After 2nd delivery to same area: **50%** ✅ (1 hit, 1 miss)
- After 3rd delivery to same area: **66%** ✅ (2 hits, 1 miss)

**This proves the model is reusing learned knowledge!**

---

### 5. Verify Smart Assignment

#### Before Learning (New Shipper)
```bash
POST http://localhost:5001/dispatcher/assign-shipper
{
  "shop_location": {"lat": 10.7769, "lon": 106.7009},
  "customer_location": {"lat": 10.7829, "lon": 106.6958}
}
```

Check the logs - you should see:
```
Finding optimal shipper among X candidates (SMART MODE)
✅ SMART ASSIGNMENT: SH001 (John) - Pickup: 2.5km, Total ETA: 12.0min (Speed: 1.00x)
```
**Speed: 1.00x** = no learning data yet

#### After 5 Deliveries (Shipper has Performance History)
Same request, but now logs show:
```
✅ SMART ASSIGNMENT: SH001 (John) - Pickup: 2.5km, Total ETA: 10.2min (Speed: 0.85x)
```
**Speed: 0.85x** = learned this shipper is 15% faster! ✅

---

### 6. Verify Shipper Performance Learning

#### Test Multiple Deliveries for Same Shipper

Complete 3 deliveries with shipper "SH001", then check MongoDB:

```javascript
db.shipper_performance.findOne({shipper_id: "SH001"})

// Expected result after 3 deliveries:
{
  shipper_id: "SH001",
  speed_multiplier: 0.92,  // Learned from actual performance
  delivery_count: 3,
  last_updated: ISODate("...")
}
```

**Watch the multiplier evolve:**
- After 1 delivery: might be 1.1 or 0.9 (single data point)
- After 3 deliveries: converges to real pattern (e.g., 0.92)
- After 10 deliveries: very stable and accurate

✅ **This is Exponential Moving Average in action!**

---

### 7. Check Node.js Logs

When a delivery completes, you should see:

```
✅ Delivery feedback sent to learning service for order 65a7b... (Shipper: SH001)
```

If you see this, the feedback loop is working! ✅

If you see this instead:
```
⚠️ Could not send learning feedback: ECONNREFUSED
```
❌ Python routing service is not running. Start it:
```bash
cd backend/RoutingService
python app.py
```

---

### 8. Check Python Logs

In the Python routing service terminal, look for:

```
📚 Learned from order 65a7b...: 720s actual vs 680s estimated (Shipper: SH001, Context: weekday_afternoon)
📍 Zone learned: 106.695_10.783 → 720s (n=1)
👤 Shipper SH001 updated: 1.06x (n=1)
🔄 Journey learned: 106.700_10.770→106.695_10.783 → 720s
```

✅ **If you see these emoji logs, all 4 learning systems are working!**

---

## Visual Proof Learning Works

### Scenario: Test Shipper Speed Learning

1. **Manually record a fast delivery:**
```bash
POST http://localhost:5001/learning/record-delivery
{
  "order_id": "TEST1",
  "shipper_id": "FAST_SHIPPER",
  "shop_location": {"lat": 10.7769, "lon": 106.7009},
  "customer_location": {"lat": 10.7829, "lon": 106.6958},
  "shipper_location": {"lat": 10.7700, "lon": 106.7000},
  "assignment_time": "2026-01-17T10:00:00Z",
  "delivery_time": "2026-01-17T10:08:00Z",
  "estimated_time_seconds": 600
}
```
Actual time: 8 minutes (480s)
Estimated: 10 minutes (600s)
**Shipper was 20% faster!**

2. **Check MongoDB:**
```javascript
db.shipper_performance.findOne({shipper_id: "FAST_SHIPPER"})
// Returns: { speed_multiplier: 0.8, ... }
```

✅ **0.8x multiplier = 20% faster than estimates!**

3. **Record another fast delivery (same shipper):**
```bash
POST http://localhost:5001/learning/record-delivery
{
  "order_id": "TEST2",
  "shipper_id": "FAST_SHIPPER",
  ...
  "estimated_time_seconds": 720,
  "assignment_time": "2026-01-17T11:00:00Z",
  "delivery_time": "2026-01-17T11:10:00Z"  // 10 min actual vs 12 min estimate
}
```

4. **Check multiplier again:**
```javascript
db.shipper_performance.findOne({shipper_id: "FAST_SHIPPER"})
// Returns: { speed_multiplier: 0.82, delivery_count: 2, ... }
```

✅ **Multiplier smoothed with EMA! (0.8 → 0.82 after adding 0.83 data point)**

---

## Expected Learning Timeline

| Deliveries | What You'll See |
|-----------|----------------|
| **0** | All collections empty, speed_multiplier = 1.0 for all |
| **1** | First documents appear, single data points |
| **3-5** | Patterns start emerging, multipliers stabilizing |
| **10+** | Accurate predictions, high cache hit rate |
| **50+** | Very reliable, smart assignment clearly better |

---

## Troubleshooting

### Learning Not Working?

**Check 1: Is Python service running?**
```bash
# Should show process on port 5001
netstat -ano | findstr :5001
```

**Check 2: Is MongoDB connected?**
```python
# In Python terminal
from pymongo import MongoClient
client = MongoClient("your_mongo_uri")
print(client.test.list_collection_names())  # Should not error
```

**Check 3: Are deliveries completing?**
```javascript
// In MongoDB Compass
db.orders.find({shipper_status: "delivered"}).limit(5)
```

**Check 4: Check Node.js console for errors**
Look for "Delivery feedback sent" messages

---

## Success Indicators

You know learning is working when:

✅ MongoDB collections have documents with `sample_count` increasing
✅ `cache_hit_rate` increases over time  
✅ Shipper `speed_multiplier` converges (stops changing wildly)
✅ Smart assignment logs show different multipliers for different shippers
✅ Same delivery zones get served from cache (faster response)
✅ Python logs show "📍 Zone learned" messages

---

## Next Steps After Verification

Once you confirm learning works:

1. **Monitor Performance**: Track cache_hit_rate weekly
2. **Compare Accuracy**: Log estimated vs actual times, measure RMSE
3. **A/B Test**: Try assignments with/without learning, compare customer satisfaction
4. **Expand Dataset**: More deliveries = better predictions
5. **Tune Parameters**: Adjust `LEARNING_RATE` in route_memory.py if needed

---

## Questions to Answer

- **Is it learning?** → Check MongoDB document counts
- **Is it accurate?** → Compare estimated vs actual times
- **Is it used?** → Check cache_hit_rate
- **Is it helping?** → Compare assignment quality before/after
- **Is it stable?** → Watch multipliers converge over time
