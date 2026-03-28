import React, { useEffect, useState, useCallback } from 'react';
import { Search, Filter, RefreshCw, FileText } from 'lucide-react';
import { fetchReports, FinalReport } from '../services/api';
import ReportCard from '../components/ReportCard';

const SOURCES = ['', 'GAZETTE', 'YARGITAY', 'DANISTAY', 'KIK'];
const SIGNALS = ['', 'RISK', 'OPPORTUNITY', 'MIXED', 'NEUTRAL'];
const DAY_OPTS = [7, 14, 30, 60, 90];

const Reports: React.FC = () => {
    const [reports, setReports] = useState<FinalReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [source, setSource] = useState('');
    const [signal, setSignal] = useState('');
    const [days, setDays] = useState(7);
    const [search, setSearch] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchReports({
                source: source || undefined,
                signal: signal || undefined,
                days, limit: 200,
            });
            setReports(data);
        } finally { setLoading(false); }
    }, [source, signal, days]);

    useEffect(() => { load(); }, [load]);

    const filtered = search
        ? reports.filter(r =>
            r.executive_summary_tr?.toLowerCase().includes(search.toLowerCase()) ||
            r.executive_summary_en?.toLowerCase().includes(search.toLowerCase()) ||
            r.court_or_authority?.toLowerCase().includes(search.toLowerCase()) ||
            r.legal_areas?.some(la => la.toLowerCase().includes(search.toLowerCase()))
        )
        : reports;

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">Raporlar</div>
                    <div className="page-subtitle">{reports.length} rapor bulundu</div>
                </div>
                <button className="btn btn-ghost" onClick={load}><RefreshCw size={14} /> Yenile</button>
            </div>

            {/* Filters */}
            <div className="filters-bar">
                <div style={{ position: 'relative', flex: '1 1 220px', maxWidth: 320 }}>
                    <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#64748B' }} />
                    <input placeholder="Arama…" value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ paddingLeft: 36 }} />
                </div>

                <select value={source} onChange={e => setSource(e.target.value)}>
                    <option value="">Tüm Kaynaklar</option>
                    {SOURCES.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
                </select>

                <select value={signal} onChange={e => setSignal(e.target.value)}>
                    <option value="">Tüm Sinyaller</option>
                    {SIGNALS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
                </select>

                <select value={days} onChange={e => setDays(Number(e.target.value))}>
                    {DAY_OPTS.map(d => <option key={d} value={d}>Son {d} gün</option>)}
                </select>
            </div>

            {/* List */}
            {loading ? <div className="spinner" /> : (
                <div className="report-grid">
                    {filtered.length > 0
                        ? filtered.map(r => <ReportCard key={r.doc_id} report={r} />)
                        : (
                            <div className="empty-state">
                                <FileText size={40} />
                                <p style={{ marginTop: 8 }}>Filtrelerle eşleşen rapor bulunamadı.</p>
                                <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => {
                                    setSource(''); setSignal(''); setDays(30); setSearch('');
                                }}>
                                    <Filter size={14} /> Filtreleri Temizle
                                </button>
                            </div>
                        )}
                </div>
            )}
        </div>
    );
};

export default Reports;
