import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, CartesianGrid
} from 'recharts';
import { FileText, AlertTriangle, TrendingUp, Clock, Zap, Loader2 } from 'lucide-react';
import { format } from 'date-fns';

import StatCard from '../components/StatCard';
import { fetchReportStats, fetchReports, triggerPipeline, ReportStats, FinalReport } from '../services/api';
import SignalBadge from '../components/SignalBadge';
import UrgencyBadge from '../components/UrgencyBadge';

// Colors for Source Chart
const SOURCE_COLORS: Record<string, string> = {
    GAZETTE: '#3B82F6', // Blue
    YARGITAY: '#8B5CF6', // Purple
    DANISTAY: '#4F46E5', // Indigo
    KIK: '#0D9488', // Teal
};

// Colors for Legal Area Pie
const AREA_COLORS = ['#3B82F6', '#8B5CF6', '#EC4899', '#F43F5E', '#F59E0B', '#10B981'];

const Dashboard: React.FC = () => {
    const [stats, setStats] = useState<ReportStats | null>(null);
    const [recent, setRecent] = useState<FinalReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [pipelineRunning, setPipelineRunning] = useState(false);
    const [toast, setToast] = useState<{ msg: string, type: 'success' | 'error' } | null>(null);
    const navigate = useNavigate();

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [s, r] = await Promise.all([fetchReportStats(7), fetchReports({ days: 7, limit: 10 })]);
            setStats(s);
            setRecent(r);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const handleRunPipeline = async () => {
        setPipelineRunning(true);
        setToast(null);
        try {
            await triggerPipeline(1);
            setToast({ msg: 'Pipeline başarıyla tetiklendi.', type: 'success' });
            // Reload stats after 3 seconds to see updates
            setTimeout(load, 3000);
        } catch (err) {
            setToast({ msg: 'Pipeline başlatılamadı.', type: 'error' });
        } finally {
            setPipelineRunning(false);
            setTimeout(() => setToast(null), 5000);
        }
    };

    const formatDate = (s: string | null | undefined) => {
        if (!s) return 'Bilinmiyor';
        try { return format(new Date(s), 'dd.MM.yyyy HH:mm'); } catch { return s; }
    };

    // Chart 1: Bar Chart Data (Source)
    const sourceBarData = stats ? Object.entries(stats.by_source).map(([name, count]) => ({
        name,
        count,
        fill: SOURCE_COLORS[name.toUpperCase()] || '#94A3B8'
    })) : [];

    // Chart 2: Pie Chart Data (Legal Area)
    const pieData = stats ? Object.entries(stats.by_legal_area).map(([name, value], i) => ({
        name,
        value,
        color: AREA_COLORS[i % AREA_COLORS.length]
    })) : [];

    const getSourceBadgeColor = (source: string) => {
        const s = source.toUpperCase();
        if (s === 'GAZETTE') return { color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' };
        if (s === 'YARGITAY') return { color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)' };
        if (s === 'DANISTAY') return { color: '#4F46E5', bg: 'rgba(79,70,229,0.12)' };
        if (s === 'KIK') return { color: '#0D9488', bg: 'rgba(13,148,136,0.12)' };
        return { color: '#64748B', bg: 'rgba(100,116,139,0.12)' };
    };

    if (loading) return <div className="spinner" />;

    return (
        <div>
            {/* Toast Notification */}
            {toast && (
                <div style={{
                    position: 'fixed', top: 80, right: 24, zIndex: 1000,
                    background: toast.type === 'success' ? '#10B981' : '#EF4444',
                    color: '#fff', padding: '12px 20px', borderRadius: 8,
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', fontWeight: 500, fontSize: 14
                }}>
                    {toast.msg}
                </div>
            )}

            {/* Header */}
            <div className="page-header" style={{ alignItems: 'flex-start' }}>
                <div>
                    <h1 className="page-title">Genel Bakış</h1>
                    <div className="page-subtitle">Sisteme genel bakış ve son tarama verileri.</div>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={handleRunPipeline}
                    disabled={pipelineRunning}
                >
                    {pipelineRunning ? <Loader2 size={16} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
                    Pipeline Çalıştır
                </button>
            </div>

            {/* Stats Row */}
            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 32 }}>
                <StatCard label="Toplam Rapor" value={stats?.total_reports ?? 0} icon={FileText} color="#3B82F6" />
                <StatCard label="Risk Sayısı" value={stats?.risk_count ?? 0} icon={AlertTriangle} color="#EF4444" />
                <StatCard label="Fırsat Sayısı" value={stats?.opportunity_count ?? 0} icon={TrendingUp} color="#22C55E" />
                <div className="card" style={{ padding: '20px 22px' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}>
                        Son Tarama
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: '#F1F5F9', marginTop: 4 }}>
                        {formatDate(stats?.last_run)}
                    </div>
                    <div style={{ position: 'absolute', right: 22, top: 20 }}>
                        <div style={{ width: 42, height: 42, borderRadius: 10, background: 'rgba(100,116,139,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Clock size={20} color="#94A3B8" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
                {/* Source Bar Chart */}
                <div className="card" style={{ padding: 24 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20, color: '#F1F5F9' }}>
                        Son 7 Günde Kaynak Bazında Rapor Sayısı
                    </h3>
                    <div style={{ height: 260 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={sourceBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis dataKey="name" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ background: '#1E293B', border: '1px solid #334155', borderRadius: 8, color: '#F1F5F9' }}
                                />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                    {sourceBarData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Legal Area Pie Chart */}
                <div className="card" style={{ padding: 24 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20, color: '#F1F5F9' }}>
                        Hukuki Alan Dağılımı
                    </h3>
                    <div style={{ height: 260 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={70}
                                    outerRadius={100}
                                    paddingAngle={2}
                                    dataKey="value"
                                >
                                    {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ background: '#1E293B', border: '1px solid #334155', borderRadius: 8, color: '#F1F5F9' }}
                                    itemStyle={{ color: '#F1F5F9' }}
                                />
                                <Legend
                                    wrapperStyle={{ fontSize: 12, color: '#94A3B8' }}
                                    formatter={(value) => <span style={{ color: '#E2E8F0' }}>{value}</span>}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Recent Reports Table */}
            <div className="card">
                <div style={{ padding: '20px 24px', borderBottom: '1px solid #334155' }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: '#F1F5F9' }}>Son Raporlar</h3>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table className="data-table" style={{ width: '100%', textAlign: 'left' }}>
                        <thead>
                            <tr>
                                <th style={{ padding: '14px 24px' }}>Tarih</th>
                                <th style={{ padding: '14px 24px' }}>Kaynak</th>
                                <th style={{ padding: '14px 24px' }}>Karar Türü</th>
                                <th style={{ padding: '14px 24px' }}>Sinyal</th>
                                <th style={{ padding: '14px 24px' }}>Aciliyet</th>
                                <th style={{ padding: '14px 24px', textAlign: 'right' }}>Detay</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recent.length === 0 ? (
                                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '40px 20px', color: '#64748B' }}>Henüz rapor bulunmuyor.</td></tr>
                            ) : (
                                recent.map((report) => {
                                    const srcBadge = getSourceBadgeColor(report.source);
                                    return (
                                        <tr key={report.doc_id}>
                                            <td style={{ padding: '14px 24px', whiteSpace: 'nowrap', fontSize: 13, color: '#94A3B8' }}>
                                                {formatDate(report.processed_at)}
                                            </td>
                                            <td style={{ padding: '14px 24px' }}>
                                                <span className="badge" style={{ color: srcBadge.color, background: srcBadge.bg }}>
                                                    {report.source || 'BİLİNMİYOR'}
                                                </span>
                                            </td>
                                            <td style={{ padding: '14px 24px', fontSize: 13, fontWeight: 500, color: '#E2E8F0' }}>
                                                {report.decision_type || '—'}
                                            </td>
                                            <td style={{ padding: '14px 24px' }}>
                                                <SignalBadge signal={report.overall_signal as any} size="sm" />
                                            </td>
                                            <td style={{ padding: '14px 24px' }}>
                                                <UrgencyBadge level={report.urgency_level as any} />
                                            </td>
                                            <td style={{ padding: '14px 24px', textAlign: 'right' }}>
                                                <button
                                                    onClick={() => navigate(`/reports/${report.doc_id}`)}
                                                    className="btn btn-ghost"
                                                    style={{ padding: '6px 12px', fontSize: 12 }}
                                                >
                                                    Görüntüle
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    );
};

export default Dashboard;
