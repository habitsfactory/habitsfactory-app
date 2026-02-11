// src/services/auth.js
import axios from 'axios'

const API_URL = '/api/auth/'

class AuthService {
    async login(email, password) {
        const response = await axios.post(API_URL + 'login/', {
            email,
            password
        })

        console.log('Login response:', response.data)

        // dj-rest-auth returns: { access, refresh, user }
        // or { access_token, refresh_token, user }
        // Handle both formats
        const accessToken = response.data.access || response.data.access_token
        const refreshToken = response.data.refresh || response.data.refresh_token

        if (accessToken) {
            localStorage.setItem('access_token', accessToken)
            localStorage.setItem('refresh_token', refreshToken)
            localStorage.setItem('user', JSON.stringify(response.data.user))
        }

        return response.data
    }

    logout() {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
    }

    async register(email, password1, password2) {
        const response = await axios.post(API_URL + 'registration/', {
            email,
            password1,
            password2
        })

        console.log('Registration response:', response.data)

        // Handle tokens if they're returned on registration
        const accessToken = response.data.access || response.data.access_token
        const refreshToken = response.data.refresh || response.data.refresh_token

        if (accessToken) {
            localStorage.setItem('access_token', accessToken)
            localStorage.setItem('refresh_token', refreshToken)
            if (response.data.user) {
                localStorage.setItem('user', JSON.stringify(response.data.user))
            }
        }

        return response.data
    }

    getCurrentUser() {
        const user = localStorage.getItem('user')
        return user ? JSON.parse(user) : null
    }

    getAccessToken() {
        return localStorage.getItem('access_token')
    }

    getRefreshToken() {
        return localStorage.getItem('refresh_token')
    }

    async refreshToken() {
        const refresh = this.getRefreshToken()

        if (!refresh) {
            throw new Error('No refresh token available')
        }

        const response = await axios.post(API_URL + 'token/refresh/', {
            refresh
        })

        if (response.data.access) {
            localStorage.setItem('access_token', response.data.access)
            return response.data.access
        }

        return null
    }
}

export default new AuthService()