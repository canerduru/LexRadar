import React, { useEffect, useState, useCallback } from 'react';
import { format } from 'date-fns';
import { Bell, RefreshCw, ExternalLink } from 'lucide-react';
import { fetchAlerts } from '../services/api';

const URGENCY_COLORS: Record<string, string> = {
    HIGH: '#EF4444', MEDIUM: '#F59E0B', LOW: '#22C55E', CRITICAL: '#FF6B6B',
};

const Alerts: React.FC = () => {
    const [alerts, setAlerts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try { setAlerts(await fetchAlerts(50)); } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const formatDate = (s: string) => {
        try { return format(new Date(s), 'dd.MM.yyyy HH:mm'); } catch { return s; }
    };

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">Uyarılar</div>
                    <div className="page-subtitle">Son 50 gönderilen uyarı</div>
                </div>
                <button className="btn btn-ghost" onClick={load}><RefreshCw size={14} /> Yenile</button>
            </div>

            {loading ? <div className="spinner" /> : (
                <div>
                    {alerts.length === 0 ? (
                        <div className="empty-state">
                            <Bell size={40} />
                            <p style={{ marginTop: 8 }}>Henüz uyarı gönderilmedi.</p>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            {alerts.map((alert, i) => {
                                const urgency = alert.urgency_level || alert.urgency || '';
                                const color = URGENCY_COLORS[urgency] || '#64748B';
                                return (
                                    <div key={i} className="card"
                                        style={{ padding: '14px 18px', borderLeft: `3px solid ${color}` }}>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                                                {urgency && (
                                                    <span className="badge" style={{ color, background: `${color}18`, fontSize: 11 }}>
                                                        {urgency}
                                                    </span>
                                                )}
                                                {alert.signal && (
                                                    <span className="badge" style={{
                                                        fontSize: 11,
                                                        color: alert.signal === 'RISK' ? '#EF4444' : alert.signal === 'OPPORTUNITY' ? '#22C55E' : '#F59E0B',
                                                        background: 'rgba(100,116,139,0.1)'
                                                    }}>
                                                        {alert.signal}
                                                    </span>
                                                )}
                                                {alert.source && (
                                                    <span style={{ fontSize: 11, color: '#64748B' }}>{alert.source}</span>
                                                )}
                                            </div>
                                            <span style={{ fontSize: 11, color: '#475569', whiteSpace: 'nowrap' }}>
                                                {formatDate(alert.sent_at || alert.timestamp || '')}
                                            </span>
                                        </div>

                                        {alert.client_name && (
                                            <div style={{ fontSize: 13, fontWeight: 600, color: '#94A3B8', marginBottom: 4 }}>
                                                👤 {alert.client_name} · {alert.company_name}
                                            </div>
                                        )}

                                        {alert.summary && (
                                            <p style={{ fontSize: 13, color: '#94A3B8', lineHeight: 1.5, marginBottom: alert.doc_id ? 8 : 0 }}>
                                                {alert.summary}
                                            </p>
                                        )}
                                        {alert.raw && !alert.summary && (
                                            <p style={{ fontSize: 12, color: '#475569', fontFamily: 'monospace' }}>{alert.raw}</p>
                                        )}

                                        {alert.doc_id && (
                                            <a href={`/reports/${alert.doc_id}`}
                                                style={{ fontSize: 12, color: '#3B82F6', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                                <ExternalLink size={12} /> Raporu Görüntüle
                                            </a>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Alerts;
