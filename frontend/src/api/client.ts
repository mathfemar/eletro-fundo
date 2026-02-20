import axios from 'axios';

// Em dev, Vite proxeia /api para localhost:8528
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const apiClient = axios.create({
    baseURL: API_BASE,
    timeout: 0,
    headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API Error]', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

export interface APIResponse<T = unknown> {
    success: boolean;
    data: T;
    error: string | null;
    timestamp: string;
}

export default apiClient;
