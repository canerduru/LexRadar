import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard, FileText, Users, Bell, LogOut, Zap, Activity,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { triggerPipeline } from '../services/api';

const NAV = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/reports', icon: FileText, label: 'Raporlar' },
    { to: '/watchlist', icon: Users, label: 'İzleme' },
    { to: '/alerts', icon: Bell, label: 'Uyarılar' },
];

const Navbar: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [running, setRunning] = React.useState(false);

    const handleLogout = async () => { await logout(); navigate('/login'); };
    const handleRun = async () => {
        setRunning(true);
        try { await triggerPipeline(1); } finally {
            setTimeout(() => setRunning(false), 3000);
        }
    };

    return (
        <nav style={{
            width: 220, minHeight: '100vh', background: '#1E293B',
            borderRight: '1px solid #334155', display: 'flex',
            flexDirection: 'column', padding: '0', position: 'sticky', top: 0,
        }}>
            {/* Logo */}
            <div style={{ padding: '24px 20px 16px', borderBottom: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                        width: 36, height: 36, background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)',
                        borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Activity size={18} color="#fff" />
                    </div>
                    <div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: '#F1F5F9' }}>LexRadar</div>
                        <div style={{ fontSize: 11, color: '#64748B' }}>Intelligence</div>
                    </div>
                </div>
            </div>

            {/* Navigation links */}
            <div style={{ flex: 1, padding: '12px 10px' }}>
                {NAV.map(({ to, icon: Icon, label }) => (
                    <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '10px 12px', borderRadius: 8, marginBottom: 2, fontSize: 14,
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? '#3B82F6' : '#94A3B8',
                        background: isActive ? 'rgba(59,130,246,0.12)' : 'transparent',
                        textDecoration: 'none', transition: 'all 150ms',
                    })}>
                        <Icon size={17} />
                        {label}
                    </NavLink>
                ))}
            </div>

            {/* Run pipeline button */}
            <div style={{ padding: '0 10px 10px' }}>
                <button className="btn btn-primary" onClick={handleRun} disabled={running}
                    style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}>
                    <Zap size={14} />
                    {running ? 'Çalışıyor…' : 'Pipeline Başlat'}
                </button>
            </div>

            {/* User info + logout */}
            <div style={{
                padding: '14px 14px', borderTop: '1px solid #334155',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
                <div style={{ overflow: 'hidden' }}>
                    <div style={{
                        fontSize: 12, fontWeight: 600, color: '#94A3B8', whiteSpace: 'nowrap',
                        overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 140
                    }}>
                        {user}
                    </div>
                    <div style={{ fontSize: 11, color: '#475569' }}>Admin</div>
                </div>
                <button onClick={handleLogout} title="Çıkış"
                    style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#64748B', padding: 4, borderRadius: 6
                    }}>
                    <LogOut size={16} />
                </button>
            </div>
        </nav>
    );
};

export default Navbar;
