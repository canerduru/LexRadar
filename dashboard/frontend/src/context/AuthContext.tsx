import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { login as apiLogin, logout as apiLogout } from '../services/api';

interface AuthContextValue {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: string | null;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('lexradar_token');
        if (token) {
            setIsAuthenticated(true);
            setUser(localStorage.getItem('lexradar_user'));
        }
        setIsLoading(false);
    }, []);

    const login = async (email: string, password: string) => {
        const token = await apiLogin(email, password);
        localStorage.setItem('lexradar_token', token);
        localStorage.setItem('lexradar_user', email);
        setUser(email);
        setIsAuthenticated(true);
    };

    const logout = async () => {
        try { await apiLogout(); } catch { }
        localStorage.removeItem('lexradar_token');
        localStorage.removeItem('lexradar_user');
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = (): AuthContextValue => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
    return ctx;
};
