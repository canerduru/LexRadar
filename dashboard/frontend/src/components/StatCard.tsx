import React from 'react';
import { LucideIcon } from 'lucide-react';

interface Props {
    label: string;
    value: number | string;
    icon: LucideIcon;
    color?: string;
    bgColor?: string;
    trend?: number; // positive = up, negative = down
}

const StatCard: React.FC<Props> = ({ label, value, icon: Icon, color = '#3B82F6', bgColor, trend }) => (
    <div className="card" style={{ padding: '20px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
                <div style={{
                    fontSize: 12, fontWeight: 600, color: '#64748B',
                    textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8
                }}>
                    {label}
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#F1F5F9' }}>{value}</div>
                {trend !== undefined && (
                    <div style={{ fontSize: 12, marginTop: 4, color: trend >= 0 ? '#22C55E' : '#EF4444' }}>
                        {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% son 7 gün
                    </div>
                )}
            </div>
            <div style={{
                width: 42, height: 42, borderRadius: 10,
                background: bgColor || `${color}20`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
                <Icon size={20} color={color} />
            </div>
        </div>
    </div>
);

export default StatCard;
