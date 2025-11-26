import mongoose from "mongoose";

const userSchema = new mongoose.Schema({
    name: {type:String,required:true},
    email:{type:String,required:true,unique:true},
    password:{type:String,required:true},
    cartData:{type:Object,default:{}},
    userFoodData: {
        type: Object, 
        default: {
            orderedItems: {},      // { food_id: count } - tracks how many times user ordered each food
            preferences: {},       // { ingredient: score } - learned ingredient preferences from descriptions
            lastUpdated: null      // timestamp of last preference update
        }
    }
},{minimize:false})

const userModel = mongoose.models.user || mongoose.model('user', userSchema);
export default userModel;