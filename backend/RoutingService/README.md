# OSM Routing Service

Custom routing service for shipperMobile app using OpenStreetMap data and A* pathfinding.

## Features

- **OpenStreetMap Integration**: Downloads and caches Vietnam road network data
- **A* Pathfinding**: Efficient route calculation with smart cost weighting
- **Pattern Learning Ready**: Infrastructure for traffic pattern and shipper preference learning
- **No External API Dependency**: Completely self-hosted routing engine

## Setup

### 1. Install Dependencies

```bash
cd backend/RoutingService
pip install -r requirements.txt
```

### 2. Download Map Data

On first run, the service will automatically download Ho Chi Minh City map data from OpenStreetMap (~50-100MB). This will be cached for future use.

### 3. Run the Service

```bash
python app.py
```

The service will start on `http://localhost:5001`

## API Endpoints

### Health Check
```
GET /health
```

### Get Map Info
```
GET /map/info
```

### Calculate Route
```
POST /route/calculate
Content-Type: application/json

{
  "start": {"lat": 10.7769, "lon": 106.7009},
  "end": {"lat": 10.7829, "lon": 106.6958},
  "use_smart_routing": false
}
```

Response:
```json
{
  "success": true,
  "route": {
    "coordinates": [[10.7769, 106.7009], ...],
    "distance_meters": 1234.5,
    "estimated_time_seconds": 180,
    "num_segments": 15
  },
  "calculation_time_ms": 45.2
}
```

## Configuration

### Download Different City/Region

Edit `app.py` and change the `initialize_routing_service()` function:

```python
# For a specific bounding box (north, south, east, west)
graph = map_loader.download_bbox_graph(
    north=10.85,
    south=10.70,
    east=106.80,
    west=106.60,
    network_type='drive'
)
```

### Network Types

- `'drive'` - For cars/motorcycles (default)
- `'walk'` - For pedestrians
- `'bike'` - For bicycles
- `'all'` - All road types

## Future Enhancements

1. **GPS Tracking**: Collect actual shipper routes for pattern learning
2. **Traffic Pattern Model**: Learn time-based traffic congestion patterns
3. **Route Preferences**: Learn which roads shippers prefer based on historical data
4. **Real-time Updates**: Dynamic cost adjustment based on current conditions

## Notes

- Map data is cached in `map_cache/` directory
- Initial download may take 2-5 minutes depending on city size
- Subsequent starts are instant (uses cached data)
