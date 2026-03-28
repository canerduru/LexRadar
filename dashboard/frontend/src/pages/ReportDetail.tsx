import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, ExternalLink, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { fetchReport, FinalReport } from '../services/api';
import SignalBadge from '../components/SignalBadge';
import UrgencyBadge from '../components/UrgencyBadge';
import SourceBadge from '../components/SourceBadge';

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
    <div className="card" style={{ padding: 22, marginBottom: 16 }}>
        <h3 style={{
            marginBottom: 14, fontSize: 13, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.04em', color: '#64748B'
        }}>{title}</h3>
        {children}
    </div>
);

const Tag: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color }) => (
    <span style={{
        display: 'inline-block', fontSize: 12, padding: '3px 10px',
        borderRadius: 20, background: color ? `${color}18` : '#273548',
        color: color || '#94A3B8', border: `1px solid ${color ? `${color}40` : '#334155'}`,
        margin: '3px 3px 0 0'
    }}>
        {children}
    </span>
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
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
            {/* Back + badges */}
            <div style={{ marginBottom: 24 }}>
                <button className="btn btn-ghost" style={{ marginBottom: 16, fontSize: 13 }}
                    onClick={() => navigate(-1)}>
                    <ArrowLeft size={14} /> Raporlar
                </button>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                    <SignalBadge signal={report.overall_signal as any} />
                    <UrgencyBadge level={report.urgency_level as any} />
                    <SourceBadge source={report.source} />
                    {report.action_required && (
                        <span className="badge" style={{ background: 'rgba(245,158,11,0.14)', color: '#F59E0B' }}>
                            <AlertTriangle size={12} /> Aksiyon Gerekli
                        </span>
                    )}
                </div>

                <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
                    {report.court_or_authority || report.document_type}
                </h1>
                <div style={{ fontSize: 13, color: '#64748B' }}>
                    {report.decision_type && <><strong>{report.decision_type}</strong> · </>}
                    İşlenme: {formatDate(report.processed_at)}
                    {report.gazette_date && ` · Gazete: ${report.gazette_date}`}
                </div>
            </div>

            {/* Summary */}
            <Section title="Özet">
                {report.executive_summary_tr && (
                    <p style={{ fontSize: 14, color: '#CBD5E1', lineHeight: 1.7, marginBottom: 14 }}>
                        🇹🇷 {report.executive_summary_tr}
                    </p>
                )}
                {report.executive_summary_en && (
                    <p style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.7 }}>
                        🇬🇧 {report.executive_summary_en}
                    </p>
                )}
            </Section>

            {/* Metadata */}
            <Section title="Metadata">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 24px', fontSize: 13 }}>
                    {[
                        ['Güven Skoru', `%${(report.confidence_score * 100).toFixed(0)}`],
                        ['Belge Türü', report.decision_type],
                        ['Kaynak', report.source],
                        ['Makam', report.court_or_authority],
                    ].map(([k, v]) => v ? (
                        <div key={k}>
                            <span style={{ color: '#64748B' }}>{k}: </span>
                            <span style={{ color: '#F1F5F9', fontWeight: 500 }}>{v}</span>
                        </div>
                    ) : null)}
                </div>

                {report.legal_areas?.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>Hukuk Alanları</div>
                        {report.legal_areas.map(la => <Tag key={la} color="#3B82F6">{la}</Tag>)}
                    </div>
                )}
                {report.affected_sectors?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>Etkilenen Sektörler</div>
                        {report.affected_sectors.map(s => <Tag key={s} color="#8B5CF6">{s}</Tag>)}
                    </div>
                )}
                {report.key_entities?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>Anahtar Varlıklar</div>
                        {report.key_entities.map(e => <Tag key={e}>{e}</Tag>)}
                    </div>
                )}
                {report.case_references?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>Dava Referansları</div>
                        {report.case_references.map(r => <Tag key={r} color="#06B6D4">{r}</Tag>)}
                    </div>
                )}
            </Section>

            {/* Risks */}
            {report.risks?.length > 0 && (
                <Section title={`Riskler (${report.risks.length})`}>
                    {report.risks.map((r: any, i: number) => (
                        <div key={i} style={{
                            padding: '12px 14px', background: 'rgba(239,68,68,0.08)',
                            borderRadius: 8, borderLeft: '3px solid #EF4444', marginBottom: 10
                        }}>
                            <div style={{ fontWeight: 600, color: '#FCA5A5', fontSize: 14 }}>{r.title}</div>
                            {r.description && <p style={{ fontSize: 13, color: '#94A3B8', marginTop: 4 }}>{r.description}</p>}
                            {r.severity && <span style={{ fontSize: 11, color: '#EF4444', marginTop: 4, display: 'block' }}>Şiddet: {r.severity}</span>}
                        </div>
                    ))}
                </Section>
            )}

            {/* Opportunities */}
            {report.opportunities?.length > 0 && (
                <Section title={`Fırsatlar (${report.opportunities.length})`}>
                    {report.opportunities.map((o: any, i: number) => (
                        <div key={i} style={{
                            padding: '12px 14px', background: 'rgba(34,197,94,0.08)',
                            borderRadius: 8, borderLeft: '3px solid #22C55E', marginBottom: 10
                        }}>
                            <div style={{ fontWeight: 600, color: '#86EFAC', fontSize: 14 }}>{o.title}</div>
                            {o.description && <p style={{ fontSize: 13, color: '#94A3B8', marginTop: 4 }}>{o.description}</p>}
                            {o.confidence && <span style={{ fontSize: 11, color: '#22C55E', marginTop: 4, display: 'block' }}>Güven: %{(o.confidence * 100).toFixed(0)}</span>}
                        </div>
                    ))}
                </Section>
            )}

            {/* Recommended actions */}
            {report.recommended_actions?.length > 0 && (
                <Section title="Önerilen Aksiyonlar">
                    {report.recommended_actions.map((a: string, i: number) => (
                        <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, fontSize: 14 }}>
                            <CheckCircle size={16} color="#22C55E" style={{ flexShrink: 0, marginTop: 2 }} />
                            <span style={{ color: '#CBD5E1' }}>{a}</span>
                        </div>
                    ))}
                </Section>
            )}

            {/* Source link */}
            {report.source_url && (
                <div style={{ marginTop: 4, marginBottom: 32 }}>
                    <a href={report.source_url} target="_blank" rel="noreferrer"
                        className="btn btn-ghost" style={{ fontSize: 13 }}>
                        <ExternalLink size={14} /> Kaynak Belgeyi Aç
                    </a>
                </div>
            )}
        </div>
    );
};

export default ReportDetail;
