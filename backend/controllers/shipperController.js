import shipperModel from "../models/shipperModel.js";
import jwt from "jsonwebtoken";
import bcrypt from "bcrypt";
import validator from "validator";

// Create JWT token
const createToken = (id) => {
    return jwt.sign({ id }, process.env.JWT_SECRET);
}

// Generate unique shipper ID
const generateShipperId = async () => {
    const count = await shipperModel.countDocuments();
    return `SHIP${String(count + 1).padStart(4, '0')}`;
}

// Login shipper
const loginShipper = async (req, res) => {
    const { email, password } = req.body;
    
    try {
        const shipper = await shipperModel.findOne({ email });

        if (!shipper) {
            return res.json({ success: false, message: "Shipper doesn't exist" });
        }

        if (!shipper.is_active) {
            return res.json({ success: false, message: "Account is deactivated" });
        }

        const isMatch = await bcrypt.compare(password, shipper.password);

        if (!isMatch) {
            return res.json({ success: false, message: "Invalid password" });
        }

        // Update status to available upon login
        await shipperModel.findByIdAndUpdate(shipper._id, { status: 'available' });

        const token = createToken(shipper._id);
        res.json({ 
            success: true, 
            message: "Logged in successfully", 
            token,
            shipper: {
                id: shipper._id,
                shipper_id: shipper.shipper_id,
                name: shipper.name,
                email: shipper.email,
                phone: shipper.phone,
                rating: shipper.rating,
                total_deliveries: shipper.total_deliveries
            }
        });

    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error logging in" });
    }
}

// Register shipper
const registerShipper = async (req, res) => {
    const { name, email, phone, password } = req.body;
    
    try {
        // Check if shipper exists by email or phone
        const existsByEmail = await shipperModel.findOne({ email });
        if (existsByEmail) {
            return res.json({ success: false, message: "Email already registered" });
        }

        const existsByPhone = await shipperModel.findOne({ phone });
        if (existsByPhone) {
            return res.json({ success: false, message: "Phone number already registered" });
        }

        // Validate email format
        if (!validator.isEmail(email)) {
            return res.json({ success: false, message: "Please enter valid email" });
        }

        // Validate password strength
        if (password.length < 8) {
            return res.json({ success: false, message: "Password must be at least 8 characters" });
        }

        // Validate phone number (Vietnamese format)
        const phoneRegex = /^(0|\+84)(3|5|7|8|9)[0-9]{8}$/;
        if (!phoneRegex.test(phone.replace(/\s/g, ''))) {
            return res.json({ success: false, message: "Please enter valid Vietnamese phone number" });
        }

        // Hash password
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password, salt);

        // Generate unique shipper ID
        const shipper_id = await generateShipperId();

        // Create new shipper
        const newShipper = new shipperModel({
            shipper_id,
            name,
            email,
            phone: phone.replace(/\s/g, ''),
            password: hashedPassword,
            status: 'offline'
        });

        const shipper = await newShipper.save();
        const token = createToken(shipper._id);

        res.json({ 
            success: true, 
            message: "Shipper registered successfully",
            token,
            shipper: {
                id: shipper._id,
                shipper_id: shipper.shipper_id,
                name: shipper.name,
                email: shipper.email,
                phone: shipper.phone
            }
        });

    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error registering shipper" });
    }
}

// Get shipper profile
const getShipperProfile = async (req, res) => {
    try {
        const shipper = await shipperModel.findById(req.body.userId).select('-password');
        
        if (!shipper) {
            return res.json({ success: false, message: "Shipper not found" });
        }

        res.json({ success: true, shipper });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error fetching profile" });
    }
}

// Update shipper location
const updateLocation = async (req, res) => {
    const { lat, lon } = req.body;
    
    try {
        const shipper = await shipperModel.findByIdAndUpdate(
            req.body.userId,
            { 
                current_location: { lat, lon },
                last_location_update: new Date()
            },
            { new: true }
        ).select('-password');

        res.json({ success: true, message: "Location updated", shipper });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error updating location" });
    }
}

// Update shipper status (available/busy/offline)
const updateStatus = async (req, res) => {
    const { status } = req.body;
    
    try {
        if (!['available', 'busy', 'offline'].includes(status)) {
            return res.json({ success: false, message: "Invalid status" });
        }

        const shipper = await shipperModel.findByIdAndUpdate(
            req.body.userId,
            { status },
            { new: true }
        ).select('-password');

        res.json({ success: true, message: "Status updated", shipper });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error updating status" });
    }
}

// Get all available shippers (for dispatcher)
const getAvailableShippers = async (req, res) => {
    try {
        const shippers = await shipperModel.find({ 
            status: 'available',
            is_active: true 
        }).select('-password');

        res.json({ 
            success: true, 
            shippers,
            total: shippers.length
        });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error fetching shippers" });
    }
}

// Assign order to shipper
const assignOrder = async (req, res) => {
    const { shipper_id, order_id } = req.body;
    
    try {
        const orderModel = (await import('../models/orderModel.js')).default;
        
        // Find and update shipper
        const shipper = await shipperModel.findOneAndUpdate(
            { shipper_id, status: 'available' },
            { 
                status: 'busy',
                current_order: order_id
            },
            { new: true }
        ).select('-password');

        if (!shipper) {
            return res.json({ success: false, message: "Shipper not available" });
        }

        // Update order with assignment details (including shipper location for learning)
        await orderModel.findByIdAndUpdate(order_id, {
            assigned_shipper: shipper._id,
            shipper_status: 'assigned',
            assignment_time: new Date(),
            shipper_location: {
                lat: shipper.current_location.lat,
                lon: shipper.current_location.lon
            }
        });

        res.json({ success: true, message: "Order assigned", shipper });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error assigning order" });
    }
}

// Complete delivery (mark shipper as available)
const completeDelivery = async (req, res) => {
    try {
        const shipper = await shipperModel.findByIdAndUpdate(
            req.body.userId,
            { 
                status: 'available',
                current_order: null,
                $inc: { total_deliveries: 1 }
            },
            { new: true }
        ).select('-password');

        res.json({ success: true, message: "Delivery completed", shipper });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error completing delivery" });
    }
}

// Update shipper rating
const updateRating = async (req, res) => {
    const { shipper_id, rating } = req.body;
    
    try {
        const shipper = await shipperModel.findOne({ shipper_id });
        
        if (!shipper) {
            return res.json({ success: false, message: "Shipper not found" });
        }

        // Calculate new average rating
        const totalDeliveries = shipper.total_deliveries;
        const currentRating = shipper.rating;
        const newRating = ((currentRating * totalDeliveries) + rating) / (totalDeliveries + 1);

        shipper.rating = Math.round(newRating * 10) / 10; // Round to 1 decimal
        await shipper.save();

        res.json({ success: true, message: "Rating updated", rating: shipper.rating });
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error updating rating" });
    }
}

// Generate random test shippers for development/testing
const generateRandomShippers = async (req, res) => {
    const { count = 20 } = req.body;
    
    try {
        // Vietnamese names for random generation
        const firstNames = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Vo', 'Dang', 'Bui', 'Do'];
        const lastNames = ['Van', 'Thi', 'Minh', 'Thanh', 'Van', 'Duc', 'Ngoc', 'Quoc', 'Hong', 'Kim'];
        const middleNames = ['An', 'Binh', 'Cuong', 'Dung', 'Hai', 'Khanh', 'Linh', 'Nam', 'Phong', 'Tuan'];
        
        // Ho Chi Minh City area bounds
        const centerLat = 10.7769;
        const centerLon = 106.7009;
        const radius = 0.1; // ~11km radius
        
        const areas = [
            'District 1', 'District 3', 'District 5', 'District 7', 
            'Binh Thanh', 'Phu Nhuan', 'Tan Binh', 'Go Vap'
        ];
        
        // Default password for test shippers
        const defaultPassword = 'shipper123';
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(defaultPassword, salt);
        
        const generatedShippers = [];
        let successCount = 0;
        
        for (let i = 0; i < count; i++) {
            try {
                // Generate random name
                const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
                const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
                const middleName = middleNames[Math.floor(Math.random() * middleNames.length)];
                const name = `${firstName} ${lastName} ${middleName}`;
                
                // Generate shipper ID
                const shipper_id = await generateShipperId();
                
                // Generate random location within Ho Chi Minh City
                const lat = centerLat + (Math.random() - 0.5) * radius;
                const lon = centerLon + (Math.random() - 0.5) * radius;
                
                // Generate unique email and phone
                const email = `${shipper_id.toLowerCase()}@shipper.test`;
                const phone = `0${Math.floor(300000000 + Math.random() * 600000000)}`;
                
                // Random area
                const area = areas[Math.floor(Math.random() * areas.length)];
                
                // Random status (mostly available for testing)
                const statuses = ['available', 'available', 'available', 'busy', 'offline'];
                const status = statuses[Math.floor(Math.random() * statuses.length)];
                
                // Create shipper
                const newShipper = new shipperModel({
                    shipper_id,
                    name,
                    email,
                    phone,
                    password: hashedPassword,
                    current_location: { lat, lon },
                    area,
                    status,
                    rating: 4.5 + Math.random() * 0.5, // 4.5-5.0
                    total_deliveries: Math.floor(Math.random() * 100),
                    vehicle_type: 'motorcycle'
                });
                
                await newShipper.save();
                generatedShippers.push({
                    shipper_id,
                    name,
                    email,
                    area,
                    status
                });
                successCount++;
                
            } catch (error) {
                console.log(`Error generating shipper ${i + 1}:`, error.message);
            }
        }
        
        res.json({ 
            success: true, 
            message: `Generated ${successCount} random shippers`,
            count: successCount,
            shippers: generatedShippers,
            note: 'Default password for all test shippers: shipper123'
        });
        
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error generating shippers" });
    }
}

// Randomize shipper locations (for testing dispatch system)
const randomizeShipperLocations = async (req, res) => {
    try {
        // Ho Chi Minh City area bounds
        const centerLat = 10.7769;
        const centerLon = 106.7009;
        const radius = 0.1; // ~11km radius
        
        // Get all active shippers
        const shippers = await shipperModel.find({ is_active: true });
        
        if (shippers.length === 0) {
            return res.json({ 
                success: false, 
                message: "No active shippers found" 
            });
        }
        
        let updatedCount = 0;
        
        // Update each shipper with a new random location
        for (const shipper of shippers) {
            try {
                // Generate random location within Ho Chi Minh City
                const lat = centerLat + (Math.random() - 0.5) * radius;
                const lon = centerLon + (Math.random() - 0.5) * radius;
                
                await shipperModel.findByIdAndUpdate(shipper._id, {
                    current_location: { lat, lon },
                    last_location_update: new Date()
                });
                
                updatedCount++;
            } catch (error) {
                console.log(`Error updating shipper ${shipper.shipper_id}:`, error.message);
            }
        }
        
        res.json({ 
            success: true, 
            message: `Randomized ${updatedCount} shipper locations`,
            count: updatedCount
        });
        
    } catch (error) {
        console.log(error);
        res.json({ success: false, message: "Error randomizing locations" });
    }
}

export { 
    loginShipper, 
    registerShipper, 
    getShipperProfile,
    updateLocation,
    updateStatus,
    getAvailableShippers,
    assignOrder,
    completeDelivery,
    updateRating,
    generateRandomShippers,
    randomizeShipperLocations
};
