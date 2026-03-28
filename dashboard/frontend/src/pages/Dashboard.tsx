import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { FileText, AlertTriangle, TrendingUp, Database, Clock, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';

import StatCard from '../components/StatCard';
import { fetchReportStats, fetchReports, ReportStats, FinalReport } from '../services/api';
import ReportCard from '../components/ReportCard';

const PIE_COLORS = { RISK: '#EF4444', OPPORTUNITY: '#22C55E', MIXED: '#F59E0B', NEUTRAL: '#64748B' };

const Dashboard: React.FC = () => {
    const [stats, setStats] = useState<ReportStats | null>(null);
    const [recent, setRecent] = useState<FinalReport[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [s, r] = await Promise.all([fetchReportStats(30), fetchReports({ days: 7, limit: 5 })]);
            setStats(s); setRecent(r);
        } finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const signalPieData = stats ? [
        { name: 'Risk', value: stats.risk_count, color: PIE_COLORS.RISK },
        { name: 'Fırsat', value: stats.opportunity_count, color: PIE_COLORS.OPPORTUNITY },
        { name: 'Karma', value: stats.mixed_count, color: PIE_COLORS.MIXED },
        { name: 'Nötr', value: stats.neutral_count, color: PIE_COLORS.NEUTRAL },
    ].filter(d => d.value > 0) : [];

    const sourceBarData = stats
        ? Object.entries(stats.by_source).map(([name, count]) => ({ name, count }))
        : [];

    const legalAreaData = stats
        ? Object.entries(stats.by_legal_area)
            .sort((a, b) => b[1] - a[1]).slice(0, 6)
            .map(([name, count]) => ({ name, count }))
        : [];

    if (loading) return <div className="spinner" />;

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">Dashboard</div>
                    <div className="page-subtitle">
                        Son 30 günün özeti
                        {stats?.last_run && ` · Son çalışma: ${format(new Date(stats.last_run), 'dd.MM HH:mm')}`}
                    </div>
                </div>
                <button className="btn btn-ghost" onClick={load}><RefreshCw size={14} /> Yenile</button>
            </div>

            {/* KPI cards */}
            <div className="stat-grid">
                <StatCard label="Toplam Rapor" value={stats?.total_reports ?? 0} icon={FileText} color="#3B82F6" />
                <StatCard label="Risk Sinyali" value={stats?.risk_count ?? 0} icon={AlertTriangle} color="#EF4444" />
                <StatCard label="Fırsat Sinyali" value={stats?.opportunity_count ?? 0} icon={TrendingUp} color="#22C55E" />
                <StatCard label="Kaynak Çeşidi" value={Object.keys(stats?.by_source ?? {}).length} icon={Database} color="#8B5CF6" />
            </div>

            {/* Charts row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 28 }}>
                {/* Signal pie */}
                <div className="card" style={{ padding: 20 }}>
                    <h3 style={{ marginBottom: 16, color: '#94A3B8', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Sinyal Dağılımı
                    </h3>
                    {signalPieData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie data={signalPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                                    paddingAngle={3} dataKey="value">
                                    {signalPieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                                </Pie>
                                <Legend formatter={(v, e: any) => (
                                    <span style={{ color: '#94A3B8', fontSize: 12 }}>{e.payload.name}</span>
                                )} />
                                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #334155', borderRadius: 8 }}
                                    labelStyle={{ color: '#F1F5F9' }} itemStyle={{ color: '#94A3B8' }} />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : <div className="empty-state">Veri yok</div>}
                </div>

                {/* Source bar */}
                <div className="card" style={{ padding: 20 }}>
                    <h3 style={{ marginBottom: 16, color: '#94A3B8', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Kaynak Bazında
                    </h3>
                    {sourceBarData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={sourceBarData} layout="vertical" margin={{ left: 0 }}>
                                <XAxis type="number" hide />
                                <YAxis type="category" dataKey="name" width={80} tick={{ fill: '#94A3B8', fontSize: 12 }} />
                                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #334155', borderRadius: 8 }}
                                    labelStyle={{ color: '#F1F5F9' }} itemStyle={{ color: '#94A3B8' }} />
                                <Bar dataKey="count" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <div className="empty-state">Veri yok</div>}
                </div>

                {/* Legal areas */}
                <div className="card" style={{ padding: 20 }}>
                    <h3 style={{ marginBottom: 16, color: '#94A3B8', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Hukuk Alanları
                    </h3>
                    {legalAreaData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={legalAreaData} layout="vertical">
                                <XAxis type="number" hide />
                                <YAxis type="category" dataKey="name" width={90} tick={{ fill: '#94A3B8', fontSize: 12 }} />
                                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #334155', borderRadius: 8 }}
                                    labelStyle={{ color: '#F1F5F9' }} itemStyle={{ color: '#94A3B8' }} />
                                <Bar dataKey="count" fill="#8B5CF6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <div className="empty-state">Veri yok</div>}
                </div>
            </div>

            {/* Recent reports */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <h2 style={{ fontSize: 16, fontWeight: 600 }}>Son Raporlar</h2>
                    <button className="btn btn-ghost" style={{ fontSize: 13 }} onClick={() => navigate('/reports')}>
                        <Clock size={13} /> Tümünü Gör
                    </button>
                </div>
                <div className="report-grid">
                    {recent.length > 0 ? recent.map(r => <ReportCard key={r.doc_id} report={r} />)
                        : <div className="empty-state">Henüz rapor yok.</div>}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
