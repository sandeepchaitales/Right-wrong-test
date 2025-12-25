import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

// Get API URL based on environment
const getApiUrl = () => {
    // In production (deployed), use relative URL
    if (process.env.NODE_ENV === 'production') {
        return '/api';
    }
    // In development, use the environment variable
    return `${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api`;
};

const API_URL = getApiUrl();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [pendingReportId, setPendingReportId] = useState(null);

    // Check authentication status on mount
    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        try {
            const response = await fetch('/api/auth/me', {
                credentials: 'include'
            });
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                setUser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const loginWithGoogle = () => {
        const redirectUrl = window.location.origin + '/auth/callback';
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    // Email/Password Registration
    const registerWithEmail = async (email, password, name) => {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password, name })
            });
            
            const text = await response.text();
            let data;
            
            try {
                data = JSON.parse(text);
            } catch (parseError) {
                console.error('Response text:', text);
                throw new Error('Registration failed - invalid response');
            }
            
            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }
            
            setUser(data);
            setShowAuthModal(false);
            return { success: true, user: data };
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, error: error.message };
        }
    };

    // Email/Password Login
    const loginWithEmail = async (email, password) => {
        try {
            const response = await fetch('/api/auth/login/email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            
            const text = await response.text();
            let data;
            
            try {
                data = JSON.parse(text);
            } catch (parseError) {
                console.error('Response text:', text);
                throw new Error('Login failed - invalid response');
            }
            
            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }
            
            setUser(data);
            setShowAuthModal(false);
            return { success: true, user: data };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    };

    const logout = async () => {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        setUser(null);
        window.location.href = '/';
    };

    const processSessionId = async (sessionId) => {
        try {
            const response = await fetch('/api/auth/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ session_id: sessionId })
            });
            
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
                return userData;
            }
            return null;
        } catch (error) {
            console.error('Session processing error:', error);
            return null;
        }
    };

    // Open auth modal with optional pending report
    const openAuthModal = (reportId = null) => {
        setPendingReportId(reportId);
        setShowAuthModal(true);
    };

    const closeAuthModal = () => {
        setShowAuthModal(false);
        setPendingReportId(null);
    };

    return (
        <AuthContext.Provider value={{ 
            user, 
            loading, 
            loginWithGoogle,
            loginWithEmail,
            registerWithEmail, 
            logout, 
            checkAuth, 
            processSessionId,
            showAuthModal,
            openAuthModal,
            closeAuthModal,
            pendingReportId
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export default AuthContext;
