import { log } from "console";
import orderModel from "../models/orderModel.js";
import userModel from "../models/userModel.js";
import foodModel from "../models/foodModel.js";
import crypto from 'crypto';
import axios from 'axios';

const frontend_url = "http://localhost:5173";

// MoMo configuration
const partnerCode = process.env.MOMO_PARTNER_CODE;
const accessKey = process.env.MOMO_ACCESS_KEY;
const secretKey = process.env.MOMO_SECRET_KEY;
const endpoint = "https://test-payment.momo.vn/v2/gateway/api/create";

// 🎯 UPDATE USER FOOD PREFERENCES FROM ORDER
const updateUserFoodPreferencesFromOrder = async (userId, items) => {
    try {
        // Get user data
        let userData = await userModel.findById(userId);
        if (!userData) {
            throw new Error("User not found");
        }

        // Initialize userFoodData if not exists
        let userFoodData = userData.userFoodData || {
            orderedItems: {},
            preferences: {},
            lastUpdated: null
        };

        // Get food details for the ordered items
        const foodIds = items.map(item => item._id);
        const foods = await foodModel.find({ _id: { $in: foodIds } });
        
        // Create food lookup map
        const foodMap = {};
        foods.forEach(food => {
            foodMap[food._id.toString()] = food;
        });

        // Update ordered items count
        items.forEach(item => {
            const foodId = item._id;
            const quantity = item.quantity || 1;
            
            if (!userFoodData.orderedItems[foodId]) {
                userFoodData.orderedItems[foodId] = 0;
            }
            userFoodData.orderedItems[foodId] += quantity;
        });

        // Update ingredient preferences from food descriptions/ingredients
        items.forEach(item => {
            const food = foodMap[item._id];
            if (food && (food.ingredients || food.description)) {
                // Use ingredients field first, fallback to description
                const ingredientText = food.ingredients || food.description || '';
                
                // Split by comma and clean up each ingredient
                const rawIngredients = ingredientText.split(',').map(ing => ing.trim().toLowerCase());
                const quantity = item.quantity || 1;
                
                rawIngredients.forEach(ingredient => {
                    // Filter out very short words and common non-food words
                    if (ingredient && ingredient.length > 2 && !ingredient.includes('fresh') && !ingredient.includes('served')) {
                        // Clean ingredient (remove extra spaces, numbers, etc.)
                        const cleanIngredient = ingredient.replace(/[^a-zA-Z\s]/g, '').trim();
                        
                        if (cleanIngredient) {
                            if (!userFoodData.preferences[cleanIngredient]) {
                                userFoodData.preferences[cleanIngredient] = 0;
                            }
                            userFoodData.preferences[cleanIngredient] += quantity;
                        }
                    }
                });
            }
        });

        // Update timestamp
        userFoodData.lastUpdated = new Date();

        // Save updated user preferences
        await userModel.findByIdAndUpdate(userId, { userFoodData });

    } catch (error) {
        throw error;
    }
};

const placeOrder = async (req, res) => {
    try {
        // Save order as usual
        const newOrder = new orderModel({
            userId: req.body.userId,
            items: req.body.items,
            amount: req.body.amount,
            address: req.body.address,
        });
        await newOrder.save();
        await userModel.findByIdAndUpdate(req.body.userId, { cartData: {} });

        // 🚀 UPDATE USER FOOD PREFERENCES AUTOMATICALLY
        try {
            await updateUserFoodPreferencesFromOrder(req.body.userId, req.body.items);
        } catch (prefError) {
            // Don't fail the order if preference update fails
        }

        // MoMo payment request (theo mẫu MoMo)
        const accessKey = 'F8BBA842ECF85';
        const secretKey = 'K951B6PE1waDMi640xX08PD3vg6EkVlz';
        const orderInfo = 'pay with MoMo';
        const partnerCode = 'MOMO';
        const redirectUrl = 'https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b';
        const ipnUrl = 'https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b';
        const requestType = "payWithMethod";
        // Amount is already in VND
        const amount = String(Math.max(1, Math.round(Number(req.body.amount))));
        const orderId = partnerCode + new Date().getTime();
        const requestId = orderId;
        const extraData = '';
        const paymentCode = 'T8Qii53fAXyUftPV3m9ysyRhEanUs9KlOPfHgpMR0ON50U10Bh+vZdpJU7VY4z+Z2y77fJHkoDc69scwwzLuW5MzeUKTwPo3ZMaB29imm6YulqnWfTkgzqRaion+EuD7FN9wZ4aXE1+mRt0gHsU193y+yxtRgpmY7SDMU9hCKoQtYyHsfFR5FUAOAKMdw2fzQqpToei3rnaYvZuYaxolprm9+/+WIETnPUDlxCYOiw7vPeaaYQQH0BF0TxyU3zu36ODx980rJvPAgtJzH1gUrlxcSS1HQeQ9ZaVM1eOK/jl8KJm6ijOwErHGbgf/hVymUQG65rHU2MWz9U8QUjvDWA==';
        const orderGroupId = '';
        const autoCapture = true;
        const lang = 'vi';

        // Create raw signature
        const rawSignature = "accessKey=" + accessKey +
            "&amount=" + amount +
            "&extraData=" + extraData +
            "&ipnUrl=" + ipnUrl +
            "&orderId=" + orderId +
            "&orderInfo=" + orderInfo +
            "&partnerCode=" + partnerCode +
            "&redirectUrl=" + redirectUrl +
            "&requestId=" + requestId +
            "&requestType=" + requestType;

        const signature = crypto.createHmac('sha256', secretKey)
            .update(rawSignature)
            .digest('hex');

        const requestBody = {
            partnerCode: partnerCode,
            partnerName: "Test",
            storeId: "MomoTestStore",
            requestId: requestId,
            amount: amount,
            orderId: orderId,
            orderInfo: orderInfo,
            redirectUrl: redirectUrl,
            ipnUrl: ipnUrl,
            lang: lang,
            requestType: requestType,
            autoCapture: autoCapture,
            extraData: extraData,
            orderGroupId: orderGroupId,
            signature: signature,
            paymentCode: paymentCode
        };

        // Send request to MoMo using axios
        let momoResponse;
        try {
            momoResponse = await axios.post(
                "https://test-payment.momo.vn/v2/gateway/api/create",
                requestBody,
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
        } catch (momoError) {
            console.log("MoMo error:", momoError.response ? momoError.response.data : momoError.message);
            return res.json({
                success: false,
                message: "MoMo API error",
                momo: momoError.response ? momoError.response.data : momoError.message
            });
        }

        // Return MoMo payment url
        if (momoResponse.data && momoResponse.data.payUrl) {
            res.json({
                success: true,
                payment_url: momoResponse.data.payUrl
            });
        } else {
            console.log("MoMo response error:", momoResponse.data);
            res.json({
                success: false,
                message: "MoMo payment failed",
                momo: momoResponse.data
            });
        }
    } catch (error) {
        res.json({ success: false, message: "Error in placing order" });
    }
}

const verifyOrder = async (req, res) =>{
    const {orderId, success} = req.body;
    try {
        if (success == "true"){
            await orderModel.findByIdAndUpdate(orderId, {payment:true});
            res.json({success:true, message:"Payment successful"});
        }
        else{
            await orderModel.findByIdAndDelete(orderId);
            res.json({success:false, message:"Payment failed"});
        }
    } catch (error) {
        console.log(error);
        res.json({success:false, message:"Error in verifying order"});
    }
}

// user orders for frontend
const userOrders = async (req,res) =>{
    try {
        const orders = await orderModel.find({userId:req.body.userId});
        res.json({success:true, data:orders});
    } catch (error) {
        res.json({success:false, message:"Error in fetching orders"});
    }
}

// Listing orders for admin
const listOrders = async(req, res) =>{
    try {
        const orders = await orderModel.find();
        res.json({success:true, data:orders});
    } catch (error) {
        res.json({success:false, message:"Error in fetching orders"});
    }
}

//api for updating order status
const updateStatus = async (req, res) =>{
    try {
        await orderModel.findByIdAndUpdate(req.body.orderId, {status:req.body.status});
        res.json({success:true, message:"Order status updated"});
    } catch (error) {
        console.log(error);
        res.json({success:false, message:"Error in updating order status"});
    }
}

// Get orders assigned to a specific shipper
const getShipperOrders = async (req, res) => {
    try {
        const { shipperId } = req.params;
        
        const orders = await orderModel.find({ 
            assigned_shipper: shipperId,
            shipper_status: { $nin: ['delivered', 'cancelled'] }
        }).sort({ assignment_time: -1 });
        
        res.json({ success: true, orders });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error fetching shipper orders" });
    }
}

// Update shipper status for an order
const updateShipperStatus = async (req, res) => {
    try {
        const { orderId } = req.params;
        const { shipper_status } = req.body;
        
        const updateData = { shipper_status };
        
        // Update timestamps based on status
        if (shipper_status === 'picked_up') {
            updateData.pickup_time = new Date();
        } else if (shipper_status === 'delivered') {
            updateData.delivery_time = new Date();
            updateData.status = 'Delivered'; // Also update main order status
        }
        
        await orderModel.findByIdAndUpdate(orderId, updateData);
        res.json({ success: true, message: "Order status updated successfully" });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error updating order status" });
    }
}

// Get order by ID (for shipper to view details)
const getOrderById = async (req, res) => {
    try {
        const { orderId } = req.params;
        const order = await orderModel.findById(orderId);
        
        if (!order) {
            return res.json({ success: false, message: "Order not found" });
        }
        
        res.json({ success: true, order });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error fetching order" });
    }
}

export { placeOrder, verifyOrder, userOrders, listOrders, updateStatus, getShipperOrders, updateShipperStatus, getOrderById };
