import express from 'express';
import authMiddleware from '../middleware/auth.js';
import { placeOrder, verifyOrder, userOrders, listOrders, updateStatus, getShipperOrders, updateShipperStatus, getOrderById } from '../controllers/orderController.js';

const orderRouter = express.Router();

orderRouter.post("/place", authMiddleware, placeOrder);
orderRouter.post("/verify", verifyOrder);
orderRouter.post("/userorders", authMiddleware, userOrders);
orderRouter.get("/list", listOrders);
orderRouter.post("/status", updateStatus);

// Shipper-related routes
orderRouter.get("/shipper/:shipperId", authMiddleware, getShipperOrders);
orderRouter.put("/shipper/status/:orderId", authMiddleware, updateShipperStatus);
orderRouter.get("/:orderId", authMiddleware, getOrderById);

export default orderRouter;