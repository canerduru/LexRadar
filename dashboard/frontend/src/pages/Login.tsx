import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Login: React.FC = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState('admin@lexradar.com');
    const [password, setPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(''); setLoading(true);
        try {
            await login(email, password);
            navigate('/');
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Giriş başarısız. Email ve şifreyi kontrol edin.');
        } finally { setLoading(false); }
    };

    return (
        <div style={{
            minHeight: '100vh', background: '#0F172A', display: 'flex',
            alignItems: 'center', justifyContent: 'center', padding: 20,
        }}>
            <div style={{ width: '100%', maxWidth: 400 }}>
                {/* Logo */}
                <div style={{ textAlign: 'center', marginBottom: 36 }}>
                    <div style={{
                        width: 56, height: 56, background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)',
                        borderRadius: 16, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        marginBottom: 16,
                    }}>
                        <Activity size={26} color="#fff" />
                    </div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: '#F1F5F9' }}>LexRadar</h1>
                    <p style={{ fontSize: 14, color: '#64748B', marginTop: 4 }}>Hukuki İstihbarat Platformu</p>
                </div>

                {/* Card */}
                <div className="card" style={{ padding: 32 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 24, color: '#F1F5F9' }}>Giriş Yap</h2>

                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: 16 }}>
                            <label>Email Adresi</label>
                            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                                autoComplete="email" required />
                        </div>

                        <div style={{ marginBottom: 24 }}>
                            <label>Şifre</label>
                            <div style={{ position: 'relative' }}>
                                <input type={showPw ? 'text' : 'password'} value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    autoComplete="current-password" required
                                    style={{ paddingRight: 44 }} />
                                <button type="button" onClick={() => setShowPw(!showPw)} style={{
                                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', cursor: 'pointer', color: '#64748B',
                                }}>
                                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div style={{
                                background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
                                borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#EF4444', marginBottom: 16
                            }}>
                                {error}
                            </div>
                        )}

                        <button type="submit" className="btn btn-primary" disabled={loading}
                            style={{ width: '100%', justifyContent: 'center', padding: '11px 0', fontSize: 15 }}>
                            {loading ? 'Giriş yapılıyor…' : 'Giriş Yap'}
                        </button>
                    </form>
                </div>

                <p style={{ textAlign: 'center', fontSize: 12, color: '#475569', marginTop: 20 }}>
                    LexRadar © 2026 · Hukuki İstihbarat
                </p>
            </div>
        </div>
    );
};

export default Login;
