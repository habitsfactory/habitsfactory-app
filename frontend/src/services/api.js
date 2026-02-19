import axios from 'axios'
import authService from './auth'

// withCredentials ensures HttpOnly auth cookies are sent on every request
const api = axios.create({
    baseURL: '/api/',
    withCredentials: true,
})

// Response interceptor: silently refresh the access cookie on 401
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        // If 401 and we haven't retried yet, attempt a silent token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            try {
                // Server sets a new access cookie from the HttpOnly refresh cookie
                await authService.refreshToken()
                return api(originalRequest)
            } catch (refreshError) {
                // Refresh failed — session expired, send to login
                await authService.logout()
                window.location.href = '/login'
                return Promise.reject(refreshError)
            }
        }

        return Promise.reject(error)
    }
)

export default api