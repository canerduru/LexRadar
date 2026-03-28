import React from 'react';

type Signal = 'OPPORTUNITY' | 'RISK' | 'MIXED' | 'NEUTRAL' | '';

const SIGNAL_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
    OPPORTUNITY: { label: 'Fırsat', color: '#22C55E', bg: 'rgba(34,197,94,0.14)', dot: '#22C55E' },
    RISK: { label: 'Risk', color: '#EF4444', bg: 'rgba(239,68,68,0.14)', dot: '#EF4444' },
    MIXED: { label: 'Karma', color: '#F59E0B', bg: 'rgba(245,158,11,0.14)', dot: '#F59E0B' },
    NEUTRAL: { label: 'Nötr', color: '#64748B', bg: 'rgba(100,116,139,0.14)', dot: '#64748B' },
};

const SignalBadge: React.FC<{ signal: Signal; size?: 'sm' | 'md' }> = ({ signal, size = 'md' }) => {
    const cfg = SIGNAL_CONFIG[signal] || SIGNAL_CONFIG.NEUTRAL;
    return (
        <span className="badge" style={{
            color: cfg.color,
            background: cfg.bg,
            fontSize: size === 'sm' ? 11 : 12,
            padding: size === 'sm' ? '2px 8px' : '3px 10px',
        }}>
            <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: cfg.dot, display: 'inline-block',
            }} />
            {cfg.label}
        </span>
    );
};

export default SignalBadge;
