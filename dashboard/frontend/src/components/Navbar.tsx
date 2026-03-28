import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Activity, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV = [
    { to: '/', label: 'Genel Bakış' },
    { to: '/reports', label: 'Raporlar' },
    { to: '/watchlist', label: 'İzleme' },
    { to: '/alerts', label: 'Uyarılar' },
];

const Navbar: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <nav style={{
            height: 60,
            background: '#0F172A',
            borderBottom: '1px solid #1E293B',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            position: 'sticky',
            top: 0,
            zIndex: 100
        }}>
            {/* Left: Logo & Links */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }} onClick={() => navigate('/')}>
                    <div style={{
                        width: 28, height: 28, background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)',
                        borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Activity size={16} color="#fff" />
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#F1F5F9' }}>LexRadar</div>
                </div>

                <div style={{ display: 'flex', gap: 4 }}>
                    {NAV.map(({ to, label }) => (
                        <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
                            padding: '6px 12px',
                            borderRadius: 6,
                            fontSize: 14,
                            fontWeight: 500,
                            color: isActive ? '#fff' : '#94A3B8',
                            background: isActive ? '#1E293B' : 'transparent',
                            textDecoration: 'none',
                            transition: 'all 150ms',
                        })}>
                            {label}
                        </NavLink>
                    ))}
                </div>
            </div>

            {/* Right: Email & Logout */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ fontSize: 14, color: '#94A3B8' }}>{user}</div>
                <button
                    onClick={handleLogout}
                    title="Çıkış Yap"
                    style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#64748B', display: 'flex', alignItems: 'center'
                    }}>
                    <LogOut size={18} />
                </button>
            </div>
        </nav>
    );
};

export default Navbar;
