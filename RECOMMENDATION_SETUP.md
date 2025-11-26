# 🚀 Vietnamese Food AI Recommendation System - Setup Guide

## 🎯 What We Built

Your Vietnamese food delivery app now has a **FREE, AI-powered recommendation system** that:

- ✅ **Learns from user behavior** - Clicks, orders, ratings automatically improve recommendations
- ✅ **Vietnamese meal patterns** - Understands breakfast (noodle soup), lunch (rice), dinner preferences  
- ✅ **Time-aware suggestions** - Different recommendations for morning, afternoon, evening
- ✅ **Thompson Sampling algorithm** - Balances popular items with personalized discovery
- ✅ **Real-time adaptation** - Gets smarter every day without manual training
- ✅ **$0 cost forever** - No API fees, no usage limits

---

## 📋 Quick Setup Instructions

### 1. Install Python Dependencies 🐍

```bash
# Navigate to the ML service directory
cd "backend/SuggestFoodModel"

# Create Python virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Install Node.js Dependencies 📦

```bash
# Navigate to backend directory  
cd backend

# Install axios for Python service communication
npm install axios

# Or if using yarn
yarn add axios
```

### 3. Start the Services 🔄

**Terminal 1 - Python ML Service:**
```bash
cd "backend/SuggestFoodModel"
venv\Scripts\activate
python app.py
```
*Python service will run on http://localhost:8000*

**Terminal 2 - Node.js Backend:**
```bash
cd backend
npm run server
```
*Node.js backend will run on http://localhost:5137*

**Terminal 3 - React Frontend:**
```bash
cd frontend
npm run dev
```
*React app will run on http://localhost:5173*

---

## 🔥 How It Works

### **Smart Recommendations Flow:**
```
User visits app → Python analyzes:
├── Current time (breakfast=noodle, lunch=rice, dinner=seafood)
├── User history (previous orders, ratings)  
├── Thompson Sampling (balances popular vs personalized)
└── Returns 8 perfect recommendations
```

### **Learning Loop:**
```
User clicks item → Python learns "this user likes this type"
User orders item → Strong positive signal  
User rates 5★ → Boosts similar recommendations
```

---

## 🎮 Testing Your AI Recommendations

### Test the ML Service Directly:

```bash
# Check if Python service is working
curl http://localhost:8000/health

# Get recommendations for a test user
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_123", "count": 8}'
```

### Test via Node.js API:

```bash
# Get recommendations through Node.js
curl -X POST http://localhost:5137/api/recommendations/recommend/test_user_123 \
  -H "Content-Type: application/json" \
  -d '{"count": 8}'

# Track a click
curl -X POST http://localhost:5137/api/recommendations/track/click \
  -H "Content-Type: application/json" \
  -d '{"userId": "test_user_123", "foodId": "food_id_here", "position": 1}'
```

---

## 📊 See It In Action

1. **Visit your app homepage** - You'll see "Recommended for you" section
2. **Different times = different foods:**
   - **Morning (5-11 AM)**: Noodle soups, light meals
   - **Afternoon (11-4 PM)**: Rice dishes, balanced meals  
   - **Evening (4-10 PM)**: Hearty meals, seafood, family dishes
3. **Click on items** - The AI learns your preferences
4. **Place orders** - Strong signal for future recommendations
5. **Rate items** - 4-5 star ratings boost similar foods

---

## 🔧 Configuration

### Environment Variables:

**backend/SuggestFoodModel/.env:**
```
MONGODB_URL=mongodb://localhost:27017/
DATABASE_NAME=food-delivery
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=True
```

**backend/.env:**
```
ML_SERVICE_URL=http://localhost:8000
```

---

## 🚨 Troubleshooting

### Python Service Won't Start:
```bash
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Node.js Can't Connect to Python:
```bash
# Check if Python service is running
curl http://localhost:8000/health

# Check Node.js logs for connection errors
npm run server
```

### No Recommendations Showing:
1. Check if MongoDB has food data
2. Verify Python service is running on port 8000
3. Check browser console for API errors
4. Python service will fallback gracefully if needed

---

## 🎯 Vietnamese Food Intelligence

Your AI automatically understands:

### **Meal Time Patterns:**
- **Sáng (Morning)**: Phở, bánh mì, coffee → Boosts "Noodle" category
- **Trưa (Lunch)**: Cơm, bún, salad → Boosts "Rice", "Noodle", "Salad"  
- **Tối (Evening)**: Family meals, seafood → Boosts "Rice", "Seafood"

### **Learning Signals:**
- **View**: +0.1 points (mild interest)
- **Click**: +0.5 points (strong interest)  
- **Add to Cart**: +0.7 points (very strong)
- **Order**: +1.0 points (maximum signal)
- **5-star Rating**: +1.0 points (love it!)
- **1-star Rating**: +0.0 points (avoid similar)

---

## 📈 Monitoring & Analytics

### Check System Performance:
```bash
# Get recommendation statistics
curl http://localhost:8000/stats

# View available foods
curl http://localhost:8000/foods
```

### Monitor Learning:
- Check console logs for interaction tracking
- Python service logs show learning updates
- Recommendations improve over time automatically

---

## 🚀 Next Steps

Your AI recommendation system is now **production-ready** and will:

1. **Learn automatically** from every user interaction
2. **Adapt to Vietnamese eating patterns** throughout the day
3. **Scale to thousands of users** without additional costs
4. **Improve recommendations daily** without manual intervention

**The more users interact, the smarter it gets! 🧠**

---

## 💡 Pro Tips

- **Let it run for 1 week** - You'll see noticeable improvement in recommendations
- **Encourage ratings** - 5-star ratings create the strongest learning signals
- **Monitor performance** - Check `/api/recommendations/stats` weekly
- **Zero maintenance** - The system learns and adapts automatically

**Your Vietnamese food delivery app now has enterprise-grade AI recommendations for $0 cost! 🎉**