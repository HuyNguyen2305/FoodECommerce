import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Use 10.0.2.2 for Android emulator, localhost for iOS
const API_BASE_URL = Platform.select({
  android: 'http://10.0.2.2:5137/api/shipper',
  ios: 'http://localhost:5137/api/shipper',
  default: 'http://localhost:5137/api/shipper',
});

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  name: string;
  email: string;
  phone: string;
  password: string;
}

export interface ShipperProfile {
  id: string;
  shipper_id: string;
  name: string;
  email: string;
  phone: string;
  rating: number;
  total_deliveries: number;
  status: 'available' | 'busy' | 'offline';
  current_location?: {
    lat: number;
    lon: number;
  };
}

export const authService = {
  async login(credentials: LoginCredentials) {
    try {
      console.log('Attempting shipper login...');
      
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();
      
      if (data.success && data.token) {
        // Store token and shipper info
        await AsyncStorage.setItem('shipper_token', data.token);
        await AsyncStorage.setItem('shipper_profile', JSON.stringify(data.shipper));
        
        console.log('Login successful:', data.shipper.name);
        return { 
          success: true, 
          token: data.token,
          shipper: data.shipper 
        };
      } else {
        console.error('Login failed:', data.message);
        return { success: false, message: data.message || 'Login failed' };
      }
    } catch (error: any) {
      console.error('Auth error:', error);
      return { success: false, message: 'Network error. Please check your connection.' };
    }
  },

  async register(credentials: RegisterCredentials) {
    try {
      console.log('Attempting shipper registration...');
      
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();
      
      if (data.success && data.token) {
        // Store token and shipper info
        await AsyncStorage.setItem('shipper_token', data.token);
        await AsyncStorage.setItem('shipper_profile', JSON.stringify(data.shipper));
        
        console.log('Registration successful:', data.shipper.name);
        return { 
          success: true, 
          token: data.token,
          shipper: data.shipper 
        };
      } else {
        console.error('Registration failed:', data.message);
        return { success: false, message: data.message || 'Registration failed' };
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      return { success: false, message: 'Network error. Please check your connection.' };
    }
  },

  async logout() {
    try {
      await AsyncStorage.removeItem('shipper_token');
      await AsyncStorage.removeItem('shipper_profile');
      console.log('Logout successful');
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false };
    }
  },

  async getToken(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem('shipper_token');
    } catch (error) {
      console.error('Error getting token:', error);
      return null;
    }
  },

  async getProfile(): Promise<ShipperProfile | null> {
    try {
      const profileStr = await AsyncStorage.getItem('shipper_profile');
      return profileStr ? JSON.parse(profileStr) : null;
    } catch (error) {
      console.error('Error getting profile:', error);
      return null;
    }
  },

  async updateProfile(profile: ShipperProfile) {
    try {
      await AsyncStorage.setItem('shipper_profile', JSON.stringify(profile));
      return { success: true };
    } catch (error) {
      console.error('Error updating profile:', error);
      return { success: false };
    }
  },

  async isLoggedIn(): Promise<boolean> {
    const token = await this.getToken();
    return !!token;
  }
};
