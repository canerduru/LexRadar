import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Reports from './pages/Reports';
import ReportDetail from './pages/ReportDetail';
import Watchlist from './pages/Watchlist';
import Alerts from './pages/Alerts';

/** Wraps protected views with the sidebar layout. */
const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { isAuthenticated, isLoading } = useAuth();
    if (isLoading) return <div style={{ minHeight: '100vh', background: '#0F172A' }} />;
    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return (
        <div className="page-layout">
            <Navbar />
            <main className="page-content">{children}</main>
        </div>
    );
};

const AppRoutes: React.FC = () => {
    const { isAuthenticated } = useAuth();
    return (
        <Routes>
            <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
            <Route path="/" element={<ProtectedLayout><Dashboard /></ProtectedLayout>} />
            <Route path="/reports" element={<ProtectedLayout><Reports /></ProtectedLayout>} />
            <Route path="/reports/:docId" element={<ProtectedLayout><ReportDetail /></ProtectedLayout>} />
            <Route path="/watchlist" element={<ProtectedLayout><Watchlist /></ProtectedLayout>} />
            <Route path="/alerts" element={<ProtectedLayout><Alerts /></ProtectedLayout>} />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
};

const App: React.FC = () => (
    <AuthProvider>
        <BrowserRouter>
            <AppRoutes />
        </BrowserRouter>
    </AuthProvider>
);

export default App;
