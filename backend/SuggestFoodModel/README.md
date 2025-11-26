# Vietnamese Food Recommendation System Setup

## Prerequisites
- Python 3.8+ installed
- pip package manager

## Setup Instructions

### 1. Create Virtual Environment
```bash
cd backend/SuggestFoodModel
python -m venv venv
```

### 2. Activate Virtual Environment
```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux  
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Environment Variables
Create a `.env` file with:
```
MONGODB_URL=mongodb://localhost:27017/food-delivery
REDIS_URL=redis://localhost:6379
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
```

### 5. Run the Service
```bash
python app.py
```

## Architecture
```
Node.js Backend → Python ML Service (Port 8000) → Recommendations
                ↓
            MongoDB (User data, Food catalog)
                ↓  
            Redis (Fast recommendation caching)
```

## Features
- Thompson Sampling for real-time learning
- Vietnamese food context (time, weather, culture)
- User interaction tracking
- Zero cost, unlimited usage
- Professional-grade algorithms