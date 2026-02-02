import { Platform } from 'react-native';
import { authService } from './auth';

// Backend API endpoint - use 10.0.2.2 for Android emulator
const API_BASE_URL = Platform.select({
  android: 'http://10.0.2.2:5137',
  ios: 'http://localhost:5137',
  default: 'http://localhost:5137',
});

export interface Order {
  _id: string;
  userId: string;
  items: Array<{
    _id: string;
    name: string;
    quantity: number;
    price: number;
  }>;
  amount: number;
  address: {
    firstName: string;
    lastName: string;
    email: string;
    street: string;
    city: string;
    state: string;
    zipcode: string;
    country: string;
    phone: string;
  };
  status: string;
  date: string;
  payment: boolean;
  // Shipper fields
  assigned_shipper?: string;
  shipper_status: 'pending' | 'assigned' | 'en_route_to_shop' | 'picked_up' | 'en_route_to_customer' | 'delivered' | 'cancelled';
  assignment_time?: string;
  pickup_time?: string;
  delivery_time?: string;
  shop_location: {
    lat: number;
    lon: number;
  };
  customer_location?: {
    lat: number;
    lon: number;
  };
  estimated_distance_meters?: number;
  estimated_time_seconds?: number;
}

export const orderService = {
  /**
   * Get all orders assigned to the current shipper
   */
  async getMyOrders(): Promise<{ success: boolean; orders?: Order[]; message?: string }> {
    try {
      const token = await authService.getToken();
      if (!token) {
        return { success: false, message: 'Not authenticated' };
      }

      const profile = await authService.getProfile();
      if (!profile) {
        return { success: false, message: 'Profile not found' };
      }

      const response = await fetch(`${API_BASE_URL}/api/order/shipper/${profile.id}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        return { success: true, orders: data.orders };
      }

      return { success: false, message: data.message || 'Failed to fetch orders' };
    } catch (error) {
      console.error('Get my orders error:', error);
      return { success: false, message: 'Cannot connect to server. Make sure backend is running on port 5137.' };
    }
  },

  /**
   * Update order status (shipper progress)
   */
  async updateOrderStatus(
    orderId: string, 
    newStatus: Order['shipper_status']
  ): Promise<{ success: boolean; message?: string }> {
    try {
      const token = await authService.getToken();
      if (!token) {
        return { success: false, message: 'Not authenticated' };
      }

      const response = await fetch(`${API_BASE_URL}/api/order/shipper/status/${orderId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ shipper_status: newStatus }),
      });

      const data = await response.json();

      if (data.success) {
        return { success: true, message: 'Status updated successfully' };
      }

      return { success: false, message: data.message || 'Failed to update status' };
    } catch (error) {
      console.error('Update order status error:', error);
      return { success: false, message: 'Cannot connect to server' };
    }
  },

  /**
   * Mark order as picked up (from shop)
   */
  async markPickedUp(orderId: string): Promise<{ success: boolean; message?: string }> {
    return this.updateOrderStatus(orderId, 'picked_up');
  },

  /**
   * Mark order as delivered (to customer)
   */
  async markDelivered(orderId: string): Promise<{ success: boolean; message?: string }> {
    return this.updateOrderStatus(orderId, 'delivered');
  },

  /**
   * Accept assigned order
   */
  async acceptOrder(orderId: string): Promise<{ success: boolean; message?: string }> {
    return this.updateOrderStatus(orderId, 'en_route_to_shop');
  },

  /**
   * Reject assigned order
   */
  async rejectOrder(orderId: string): Promise<{ success: boolean; message?: string }> {
    try {
      const token = await authService.getToken();
      if (!token) {
        return { success: false, message: 'Not authenticated' };
      }

      const response = await fetch(`${API_BASE_URL}/api/order/shipper/reject/${orderId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        return { success: true, message: 'Order rejected' };
      }

      return { success: false, message: data.message || 'Failed to reject order' };
    } catch (error) {
      console.error('Reject order error:', error);
      return { success: false, message: 'Cannot connect to server' };
    }
  },

  /**
   * Get order details by ID
   */
  async getOrderById(orderId: string): Promise<{ success: boolean; order?: Order; message?: string }> {
    try {
      const token = await authService.getToken();
      if (!token) {
        return { success: false, message: 'Not authenticated' };
      }

      const response = await fetch(`${API_BASE_URL}/api/order/${orderId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        return { success: true, order: data.order };
      }

      return { success: false, message: data.message || 'Order not found' };
    } catch (error) {
      console.error('Get order error:', error);
      return { success: false, message: 'Cannot connect to server' };
    }
  },
};
