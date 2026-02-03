import axios from 'axios';
import { env } from './env';

export const api = axios.create({
  baseURL: env.apiUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para manejo de errores global
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Ejemplo de tipado espejo con tu backend
export interface Lead {
  id: string;
  name: string;
  website: string | null;
  status: 'caliente' | 'tibio' | 'frio';
  ai_score: number;
}