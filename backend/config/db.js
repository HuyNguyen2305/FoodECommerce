import mongoose from "mongoose";

export const connectDB = async() => {
    await mongoose.connect('mongodb+srv://huyworkandcontact_db_user:Slenderman23*@cluster0.9vsew15.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0').then(()=>console.log("DB Connected"));
}