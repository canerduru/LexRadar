import React from 'react';

type Level = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | '';

const URGENCY: Record<string, { label: string; color: string; bg: string }> = {
    CRITICAL: { label: 'Kritik', color: '#EF4444', bg: 'rgba(239,68,68,0.14)' },
    HIGH: { label: 'Yüksek', color: '#F97316', bg: 'rgba(249,115,22,0.14)' },
    MEDIUM: { label: 'Orta', color: '#F59E0B', bg: 'rgba(245,158,11,0.14)' },
    LOW: { label: 'Düşük', color: '#22C55E', bg: 'rgba(34,197,94,0.14)' },
};

const UrgencyBadge: React.FC<{ level: Level }> = ({ level }) => {
    const cfg = URGENCY[level] || { label: level || '—', color: '#64748B', bg: 'rgba(100,116,139,0.14)' };
    return (
        <span className="badge" style={{ color: cfg.color, background: cfg.bg }}>
            {cfg.label}
        </span>
    );
};

export default UrgencyBadge;
