import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, ExternalLink, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { fetchReport, FinalReport } from '../services/api';
import SignalBadge from '../components/SignalBadge';
import UrgencyBadge from '../components/UrgencyBadge';
import SourceBadge from '../components/SourceBadge';

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
    <div className="card" style={{ padding: 24, marginBottom: 20 }}>
        <h3 style={{
            marginBottom: 16, fontSize: 13, fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.04em', color: '#94A3B8'
        }}>{title}</h3>
        {children}
    </div>
);

const Tag: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color }) => (
    <span style={{
        display: 'inline-flex', fontSize: 12, padding: '4px 12px',
        borderRadius: 20, background: color ? `${color}18` : '#1E293B',
        color: color || '#94A3B8', border: `1px solid ${color ? `${color}40` : '#334155'}`,
        margin: '0 8px 8px 0', fontWeight: 500
    }}>
        {children}
    </span>
);

const ProgressBar: React.FC<{ value: number; color: string }> = ({ value, color }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
        <div style={{ flex: 1, height: 6, background: '#1E293B', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${value * 100}%`, height: '100%', background: color, borderRadius: 3 }} />
        </div>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#94A3B8', width: 40, textAlign: 'right' }}>
            %{(value * 100).toFixed(0)}
        </span>
    </div>
);

const ReportDetail: React.FC = () => {
    const { docId } = useParams<{ docId: string }>();
    const navigate = useNavigate();
    const [report, setReport] = useState<FinalReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!docId) return;
        fetchReport(docId).then(setReport).catch(() => setError('Rapor bulunamadı.')).finally(() => setLoading(false));
    }, [docId]);

    if (loading) return <div className="spinner" />;
    if (error || !report) return (
        <div className="empty-state">
            <XCircle size={40} />
            <p style={{ marginTop: 8 }}>{error || 'Rapor yüklenemedi.'}</p>
            <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate(-1)}>
                <ArrowLeft size={14} /> Geri
            </button>
        </div>
    );

    const formatDate = (s: string) => {
        try { return format(new Date(s), 'dd MMMM yyyy HH:mm'); } catch { return s; }
    };

    return (
        <div style={{ maxWidth: 960, margin: '0 auto', paddingBottom: 40 }}>
            {/* Back Button */}
            <button className="btn btn-ghost" style={{ marginBottom: 20, fontSize: 13 }}
                onClick={() => navigate(-1)}>
                <ArrowLeft size={16} /> Raporlara Dön
            </button>

            {/* Action Required Banner */}
            {report.action_required && (
                <div style={{
                    background: 'linear-gradient(90deg, #EF4444 0%, #B91C1C 100%)',
                    color: '#fff', padding: '14px 20px', borderRadius: 8, display: 'flex',
                    alignItems: 'center', gap: 12, marginBottom: 24, boxShadow: '0 4px 6px -1px rgba(239,68,68,0.2)'
                }}>
                    <AlertTriangle size={20} />
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 15 }}>Aksiyon Gerektiren Gelişme</div>
                        <div style={{ fontSize: 13, opacity: 0.9 }}>Bu evrakta acil önem taşıyan bildirimler bulunmaktadır, "Önerilen Aksiyonlar" bölümünü inceleyin.</div>
                    </div>
                </div>
            )}

            {/* Header Section */}
            <div style={{ marginBottom: 32 }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 16 }}>
                    <SourceBadge source={report.source} />
                    {report.decision_type && (
                        <span style={{ fontSize: 12, color: '#94A3B8', fontWeight: 600, background: '#1E293B', padding: '4px 12px', borderRadius: 20, border: '1px solid #334155' }}>
                            {report.decision_type}
                        </span>
                    )}
                </div>

                <h1 style={{ fontSize: 26, fontWeight: 800, marginBottom: 12, color: '#F1F5F9', lineHeight: 1.3 }}>
                    {report.court_or_authority || report.document_type || 'İsimsiz Belge'}
                </h1>

                <div style={{ fontSize: 14, color: '#64748B', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
                    <span>{formatDate(report.processed_at)}</span>
                    {report.gazette_date && (
                        <>
                            <span>•</span>
                            <span>Gazete: {report.gazette_date}</span>
                        </>
                    )}
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
                    <SignalBadge signal={report.overall_signal as any} size="md" />
                    <UrgencyBadge level={report.urgency_level as any} />

                    {report.source_url && (
                        <a href={report.source_url} target="_blank" rel="noreferrer"
                            className="btn btn-primary" style={{ fontSize: 13, marginLeft: 'auto' }}>
                            Kaynağa Git <ExternalLink size={14} />
                        </a>
                    )}
                </div>
            </div>

            {/* Executive Summary */}
            <Section title="Yönetici Özeti (Executive Summary)">
                {report.executive_summary_tr && (
                    <p style={{ fontSize: 16, color: '#F1F5F9', lineHeight: 1.7, marginBottom: 16, fontWeight: 500 }}>
                        {report.executive_summary_tr}
                    </p>
                )}
                {report.executive_summary_en && (
                    <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, paddingLeft: 16, borderLeft: '3px solid #334155' }}>
                        {report.executive_summary_en}
                    </p>
                )}
            </Section>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                {/* Hukuki Alanlar & Sektörler */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {report.legal_areas?.length > 0 && (
                        <div className="card" style={{ padding: 24, flex: 1 }}>
                            <h3 style={{ marginBottom: 14, fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748B' }}>
                                Hukuki Alanlar
                            </h3>
                            <div>{report.legal_areas.map(la => <Tag key={la} color="#8B5CF6">{la}</Tag>)}</div>
                        </div>
                    )}
                    {report.affected_sectors?.length > 0 && (
                        <div className="card" style={{ padding: 24, flex: 1 }}>
                            <h3 style={{ marginBottom: 14, fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748B' }}>
                                Etkilenen Sektörler
                            </h3>
                            <div>{report.affected_sectors.map(s => <Tag key={s} color="#3B82F6">{s}</Tag>)}</div>
                        </div>
                    )}
                </div>

                {/* Temel Aktörler & Dava Ref */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {report.key_entities?.length > 0 && (
                        <div className="card" style={{ padding: 24, flex: 1 }}>
                            <h3 style={{ marginBottom: 14, fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748B' }}>
                                Temel Aktörler / Kurumlar
                            </h3>
                            <div>{report.key_entities.map(e => <Tag key={e} color="#10B981">{e}</Tag>)}</div>
                        </div>
                    )}
                    {report.case_references?.length > 0 && (
                        <div className="card" style={{ padding: 24, flex: 1 }}>
                            <h3 style={{ marginBottom: 14, fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748B' }}>
                                Dava ve İhale Referansları
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {report.case_references.map(r => (
                                    <code key={r} style={{ background: '#0F172A', padding: '8px 12px', borderRadius: 6, fontSize: 13, color: '#38BDF8', border: '1px solid #1E293B', fontFamily: 'monospace' }}>
                                        {r}
                                    </code>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Risks */}
            {report.risks?.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: '#F1F5F9', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <AlertTriangle size={20} color="#EF4444" /> Tespit Edilen Riskler ({report.risks.length})
                    </h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
                        {report.risks.map((r: any, i: number) => (
                            <div key={i} className="card" style={{ padding: 20, borderLeft: '4px solid #EF4444' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                    <div style={{ fontWeight: 700, color: '#FCA5A5', fontSize: 15 }}>{r.title}</div>
                                    {r.severity && (
                                        <span style={{ fontSize: 11, background: 'rgba(239,68,68,0.15)', color: '#EF4444', padding: '3px 8px', borderRadius: 6, fontWeight: 700, textTransform: 'uppercase' }}>
                                            {r.severity}
                                        </span>
                                    )}
                                </div>
                                {r.description && <p style={{ fontSize: 14, color: '#CBD5E1', lineHeight: 1.6, marginBottom: 12 }}>{r.description}</p>}

                                {/* Simulated confidence/severity bar for Risk */}
                                <div style={{ marginTop: 12 }}>
                                    <div style={{ fontSize: 11, color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Risk Ağırlığı</div>
                                    <ProgressBar value={r.severity?.toUpperCase() === 'HIGH' ? 0.9 : r.severity?.toUpperCase() === 'MEDIUM' ? 0.6 : 0.4} color="#EF4444" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Opportunities */}
            {report.opportunities?.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: '#F1F5F9', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <CheckCircle size={20} color="#22C55E" /> Tespit Edilen Fırsatlar ({report.opportunities.length})
                    </h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
                        {report.opportunities.map((o: any, i: number) => (
                            <div key={i} className="card" style={{ padding: 20, borderLeft: '4px solid #22C55E' }}>
                                <div style={{ fontWeight: 700, color: '#86EFAC', fontSize: 15, marginBottom: 8 }}>{o.title}</div>
                                {o.description && <p style={{ fontSize: 14, color: '#CBD5E1', lineHeight: 1.6, marginBottom: 12 }}>{o.description}</p>}

                                {o.confidence !== undefined && (
                                    <div style={{ marginTop: 12 }}>
                                        <div style={{ fontSize: 11, color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>Tespit Güven Skoru</div>
                                        <ProgressBar value={o.confidence} color="#22C55E" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recommended actions */}
            {report.recommended_actions?.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: '#F1F5F9' }}>
                        Önerilen Aksiyonlar
                    </h2>
                    <div className="card" style={{ padding: '24px 32px' }}>
                        <ol style={{ margin: 0, paddingLeft: 16, color: '#CBD5E1', fontSize: 15, lineHeight: 1.8 }}>
                            {report.recommended_actions.map((a: string, i: number) => (
                                <li key={i} style={{ marginBottom: 12, paddingLeft: 8 }}>
                                    <span style={{ color: '#F1F5F9', fontWeight: 500 }}>{a}</span>
                                </li>
                            ))}
                        </ol>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReportDetail;
