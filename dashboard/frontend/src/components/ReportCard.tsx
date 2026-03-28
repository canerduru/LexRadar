import React from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ChevronRight, AlertTriangle } from 'lucide-react';
import { FinalReport } from '../services/api';
import SignalBadge from './SignalBadge';
import UrgencyBadge from './UrgencyBadge';
import SourceBadge from './SourceBadge';

interface Props { report: FinalReport; }

const ReportCard: React.FC<Props> = ({ report }) => {
    const navigate = useNavigate();

    const formatDate = (s: string) => {
        try { return format(new Date(s), 'dd.MM.yyyy HH:mm'); } catch { return s; }
    };

    const leftBorderColor =
        report.overall_signal === 'RISK' ? '#EF4444' :
            report.overall_signal === 'OPPORTUNITY' ? '#22C55E' :
                report.overall_signal === 'MIXED' ? '#F59E0B' : '#334155';

    return (
        <div className="card" onClick={() => navigate(`/reports/${report.doc_id}`)}
            style={{
                padding: '16px 20px', cursor: 'pointer', borderLeft: `3px solid ${leftBorderColor}`,
                transition: 'background 150ms'
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#273548')}
            onMouseLeave={e => (e.currentTarget.style.background = '')}>

            {/* Top row: badges + date */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
                <SignalBadge signal={report.overall_signal as any} size="sm" />
                <UrgencyBadge level={report.urgency_level as any} />
                <SourceBadge source={report.source} />
                {report.action_required && (
                    <span className="badge" style={{ color: '#F59E0B', background: 'rgba(245,158,11,0.12)' }}>
                        <AlertTriangle size={11} /> Aksiyon Gerekli
                    </span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#64748B' }}>
                    {formatDate(report.processed_at)}
                </span>
            </div>

            {/* Summary */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9', marginBottom: 4, lineHeight: 1.4 }}>
                        {report.decision_type && (
                            <span style={{
                                fontSize: 11, color: '#64748B', marginRight: 6,
                                background: '#273548', padding: '2px 7px', borderRadius: 4
                            }}>
                                {report.decision_type}
                            </span>
                        )}
                        {report.court_or_authority}
                    </div>
                    <p style={{
                        fontSize: 13, color: '#94A3B8', lineHeight: 1.5,
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'
                    }}>
                        {report.executive_summary_tr || report.executive_summary_en}
                    </p>
                </div>
                <ChevronRight size={16} color="#475569" style={{ flexShrink: 0, marginTop: 4 }} />
            </div>

            {/* Tags */}
            {report.legal_areas?.length > 0 && (
                <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                    {report.legal_areas.slice(0, 4).map(la => (
                        <span key={la} style={{
                            fontSize: 11, color: '#64748B',
                            background: '#273548', padding: '2px 8px', borderRadius: 20, border: '1px solid #334155'
                        }}>
                            {la}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ReportCard;
