import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authService } from '../services/auth';

const LoginScreen = ({ onLoginSuccess }: { onLoginSuccess?: () => void }) => {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Error', 'Please enter email and password');
      return;
    }

    setLoading(true);
    try {
      const result = await authService.login({ 
        email: email.trim(), 
        password 
      });
      
      if (result.success) {
        Alert.alert('Success', `Welcome back, ${result.shipper?.name}!`);
        onLoginSuccess && onLoginSuccess();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error) {
      Alert.alert('Error', 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!name.trim() || !email.trim() || !phone.trim() || !password.trim()) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    if (password.length < 8) {
      Alert.alert('Error', 'Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const result = await authService.register({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        password,
      });
      
      if (result.success) {
        Alert.alert('Success', `Welcome, ${result.shipper?.name}!`);
        onLoginSuccess && onLoginSuccess();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error) {
      Alert.alert('Error', 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>
          {isRegisterMode ? 'Shipper Registration' : 'Shipper Login'}
        </Text>
        <Text style={styles.subtitle}>
          {isRegisterMode ? 'Create your shipper account' : 'Welcome back!'}
        </Text>
      </View>

      {!isRegisterMode && (
        <View style={styles.testInfo}>
          <Text style={styles.testInfoTitle}>Test Credentials:</Text>
          <Text style={styles.testInfoText}>Email: ship0001@shipper.local</Text>
          <Text style={styles.testInfoText}>Password: shipper123</Text>
        </View>
      )}

      {isRegisterMode && (
        <TextInput
          style={styles.input}
          placeholder="Full Name"
          placeholderTextColor="#666"
          value={name}
          onChangeText={setName}
          editable={!loading}
          autoCapitalize="words"
        />
      )}
      
      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor="#666"
        value={email}
        onChangeText={setEmail}
        editable={!loading}
        keyboardType="email-address"
        autoCapitalize="none"
      />

      {isRegisterMode && (
        <TextInput
          style={styles.input}
          placeholder="Phone (e.g. 0901234567)"
          placeholderTextColor="#666"
          value={phone}
          onChangeText={setPhone}
          editable={!loading}
          keyboardType="phone-pad"
        />
      )}
      
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#666"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
        editable={!loading}
      />

      {isRegisterMode && (
        <Text style={styles.hint}>Password must be at least 8 characters</Text>
      )}

      <TouchableOpacity 
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={isRegisterMode ? handleRegister : handleLogin}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>
            {isRegisterMode ? 'Register' : 'Login'}
          </Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity 
        style={styles.switchButton}
        onPress={() => setIsRegisterMode(!isRegisterMode)}
        disabled={loading}
      >
        <Text style={styles.switchText}>
          {isRegisterMode 
            ? 'Already have an account? Login' 
            : "Don't have an account? Register"}
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
    backgroundColor: '#f5f5f5',
  },
  header: {
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 15,
    marginBottom: 15,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  hint: {
    fontSize: 12,
    color: '#666',
    marginTop: -10,
    marginBottom: 15,
    paddingLeft: 5,
  },
  button: {
    backgroundColor: '#4285F4',
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  switchButton: {
    marginTop: 20,
    paddingVertical: 10,
  },
  switchText: {
    color: '#4285F4',
    textAlign: 'center',
    fontSize: 16,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  testInfo: {
    backgroundColor: '#e3f2fd',
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#4285F4',
  },
  testInfoTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1565c0',
    marginBottom: 4,
  },
  testInfoText: {
    fontSize: 11,
    color: '#1976d2',
    fontFamily: 'monospace',
  },
});

export default LoginScreen;
