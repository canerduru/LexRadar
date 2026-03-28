import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login: React.FC = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    // Hardcoded test credentials
    const [email, setEmail] = useState('admin@lexradar.com');
    const [password, setPassword] = useState('lexradar2024');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
            // Redirect to dashboard (assuming '/' routes to dashboard in App.tsx, but will use '/' as asked implicitly, or '/dashboard' if we had a dedicated route. App.tsx maps '/' to Dashboard component).
            navigate('/');
        } catch (err: any) {
            setError('Geçersiz kimlik bilgileri');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: '#0F172A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            fontFamily: 'Inter, sans-serif'
        }}>
            <div style={{
                background: '#FFFFFF',
                borderRadius: '12px', // rounded-xl roughly
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)', // shadow-2xl
                width: '100%',
                maxWidth: '400px',
                padding: '40px 32px',
                color: '#0F172A' // Dark text on white card
            }}>

                {/* Logo and Tagline */}
                <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                    <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚖️</div>
                    <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, color: '#0F172A' }}>LexRadar</h1>
                    <p style={{ fontSize: '14px', color: '#64748B', marginTop: '6px', margin: 0 }}>
                        Hukuki İstihbarat Platformu
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#475569', marginBottom: '6px' }}>
                            Email Adresi
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            style={{
                                width: '100%',
                                padding: '10px 14px',
                                background: '#FFFFFF',
                                border: '1px solid #CBD5E1',
                                borderRadius: '6px',
                                color: '#0F172A',
                                fontSize: '14px',
                                outline: 'none',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '24px' }}>
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#475569', marginBottom: '6px' }}>
                            Şifre
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            style={{
                                width: '100%',
                                padding: '10px 14px',
                                background: '#FFFFFF',
                                border: '1px solid #CBD5E1',
                                borderRadius: '6px',
                                color: '#0F172A',
                                fontSize: '14px',
                                outline: 'none',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            background: '#FEF2F2',
                            color: '#EF4444',
                            padding: '10px',
                            borderRadius: '6px',
                            fontSize: '13px',
                            textAlign: 'center',
                            marginBottom: '16px',
                            border: '1px solid #FECACA'
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%',
                            background: '#3B82F6',
                            color: '#FFFFFF',
                            border: 'none',
                            padding: '10px 0',
                            borderRadius: '6px',
                            fontSize: '15px',
                            fontWeight: 500,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                            transition: 'background 150ms'
                        }}
                    >
                        {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
