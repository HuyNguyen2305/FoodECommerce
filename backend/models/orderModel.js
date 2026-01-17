import mongoose from "mongoose";

const orderSchema = new mongoose.Schema({
    userId: {type:String, required:true},
    items: {type:Array, required:true},
    amount: {type:Number, required:true},
    address: {type:Object, required:true},
    status: {type:String, default:"Food Processing"},
    date: {type:Date, default:Date.now},
    payment: {type:Boolean, default:false},
    // Shipper assignment fields
    assigned_shipper: {type: mongoose.Schema.Types.ObjectId, ref: 'shipper', default: null},
    shipper_status: {type: String, enum: ['pending', 'assigned', 'en_route_to_shop', 'picked_up', 'en_route_to_customer', 'delivered', 'cancelled'], default: 'pending'},
    assignment_time: {type: Date, default: null},
    pickup_time: {type: Date, default: null},
    delivery_time: {type: Date, default: null},
    // Shipper starting location (for learning complete journey)
    shipper_location: {
        lat: {type: Number, default: null},
        lon: {type: Number, default: null}
    },
    // Route information
    shop_location: {
        lat: {type: Number, default: 10.7769},
        lon: {type: Number, default: 106.7009}
    },
    customer_location: {
        lat: {type: Number, default: null},
        lon: {type: Number, default: null}
    },
    estimated_distance_meters: {type: Number, default: null},
    estimated_time_seconds: {type: Number, default: null},
})

const orderModel = mongoose.model.order || mongoose.model("order", orderSchema);

export default orderModel;