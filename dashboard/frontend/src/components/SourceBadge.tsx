import React from 'react';

const SOURCE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
    GAZETTE: { label: 'Resmi Gazete', color: '#3B82F6', bg: 'rgba(59,130,246,0.12)', icon: '📰' },
    YARGITAY: { label: 'Yargıtay', color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)', icon: '⚖️' },
    DANISTAY: { label: 'Danıştay', color: '#06B6D4', bg: 'rgba(6,182,212,0.12)', icon: '🏛️' },
    KIK: { label: 'KİK', color: '#10B981', bg: 'rgba(16,185,129,0.12)', icon: '📋' },
};

const SourceBadge: React.FC<{ source: string }> = ({ source }) => {
    const key = (source || '').toUpperCase();
    const cfg = SOURCE_CONFIG[key] || {
        label: source || 'Bilinmiyor', color: '#64748B',
        bg: 'rgba(100,116,139,0.12)', icon: '📄',
    };
    return (
        <span className="badge" style={{ color: cfg.color, background: cfg.bg, fontSize: 12 }}>
            {cfg.icon} {cfg.label}
        </span>
    );
};

export default SourceBadge;
