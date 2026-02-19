// src/services/auth.js
import axios from 'axios'

const API_URL = '/api/auth/'

class AuthService {
    async login(email, password) {
        // Tokens are stored as HttpOnly cookies by the server — never in JS.
        const response = await axios.post(API_URL + 'login/', {
            email,
            password
        }, { withCredentials: true })

        // Store only non-sensitive user profile info
        if (response.data.user) {
            sessionStorage.setItem('user', JSON.stringify(response.data.user))
        }

        return response.data
    }

    async logout() {
        try {
            // Blacklist the refresh token on the server
            await axios.post(API_URL + 'logout/', {}, { withCredentials: true })
        } catch {
            // Best-effort: always clear local state even if the request fails
        }
        sessionStorage.removeItem('user')
    }

    async register(username, email, password1, password2, inviteToken) {
        const response = await axios.post(API_URL + 'registration/', {
            username,
            email,
            password1,
            password2,
            invite_token: inviteToken
        }, { withCredentials: true })

        if (response.data.user) {
            sessionStorage.setItem('user', JSON.stringify(response.data.user))
        }

        return response.data
    }

    getCurrentUser() {
        const user = sessionStorage.getItem('user')
        return user ? JSON.parse(user) : null
    }

    isAuthenticated() {
        // Client-side indicator only — actual auth is enforced server-side via HttpOnly cookies.
        return !!this.getCurrentUser()
    }

    async refreshToken() {
        // The browser sends the HttpOnly refresh cookie automatically.
        // The server responds by setting a new access cookie.
        await axios.post(API_URL + 'token/refresh/', {}, { withCredentials: true })
    }
}

export default new AuthService()