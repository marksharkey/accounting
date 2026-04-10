import { create } from 'zustand';
import apiClient from '../api/client';

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('pp_token') || null,
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await apiClient.post('/auth/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const token = response.data.access_token;
      localStorage.setItem('pp_token', token);

      const meResponse = await apiClient.get('/auth/me');
      set({ user: meResponse.data, token, isLoading: false });

      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      set({ error: message, isLoading: false });
      return { success: false, error: message };
    }
  },

  logout: () => {
    localStorage.removeItem('pp_token');
    set({ user: null, token: null, error: null });
  },

  me: async () => {
    try {
      const response = await apiClient.get('/auth/me');
      set({ user: response.data });
      return response.data;
    } catch (error) {
      set({ user: null, token: null });
      throw error;
    }
  },
}));
