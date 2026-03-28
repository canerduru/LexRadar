import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { Plus, Trash2, Users, RefreshCw } from 'lucide-react';
import { fetchWatchlist, addWatchlistItem, deleteWatchlistItem, WatchlistItem } from '../services/api';

const SECTORS = ['TEKNOLOJI', 'FINANS', 'INSAAT', 'ILAC', 'ENERJI', 'DIGER'];
const LEGAL_AREAS = ['REKABET', 'VERGI', 'IS_HUKUKU', 'KVKK', 'IHALE', 'SIRKETLER', 'CEZA', 'IDARE'];

const blank = (): Omit<WatchlistItem, 'id' | 'created_at'> => ({
    client_name: '', company_name: '', sector: 'TEKNOLOJI',
    legal_areas: [], case_references: [], watchlist_keywords: [],
    alert_threshold: 0.75, notes: '',
});

const Watchlist: React.FC = () => {
    const [items, setItems] = useState<WatchlistItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(blank());
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        try { setItems(await fetchWatchlist()); } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const handleSave = async () => {
        if (!form.client_name || !form.company_name) return;
        setSaving(true);
        try {
            const added = await addWatchlistItem(form);
            setItems(prev => [added, ...prev]);
            setForm(blank()); setShowForm(false);
        } finally { setSaving(false); }
    };

    const handleDelete = async (id: string) => {
        setDeletingId(id);
        try {
            await deleteWatchlistItem(id);
            setItems(prev => prev.filter(i => i.id !== id));
        } finally { setDeletingId(null); }
    };

    const toggleArea = (area: string) => {
        setForm(f => ({
            ...f, legal_areas: f.legal_areas.includes(area)
                ? f.legal_areas.filter(a => a !== area) : [...f.legal_areas, area],
        }));
    };

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">İzleme Listesi</div>
                    <div className="page-subtitle">{items.length} müşteri takipte</div>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                    <button className="btn btn-ghost" onClick={load}><RefreshCw size={14} /> Yenile</button>
                    <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
                        <Plus size={15} /> Müşteri Ekle
                    </button>
                </div>
            </div>

            {/* Add form */}
            {showForm && (
                <div className="card" style={{ padding: 24, marginBottom: 20 }}>
                    <h3 style={{ marginBottom: 18 }}>Yeni Müşteri Ekle</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                        <div><label>Müşteri Adı *</label>
                            <input value={form.client_name} onChange={e => setForm({ ...form, client_name: e.target.value })} /></div>
                        <div><label>Şirket *</label>
                            <input value={form.company_name} onChange={e => setForm({ ...form, company_name: e.target.value })} /></div>
                        <div><label>Sektör</label>
                            <select value={form.sector} onChange={e => setForm({ ...form, sector: e.target.value as any })}>
                                {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
                            </select></div>
                        <div><label>Uyarı Eşiği (%{Math.round(form.alert_threshold * 100)})</label>
                            <input type="range" min={0.5} max={1} step={0.05} value={form.alert_threshold}
                                onChange={e => setForm({ ...form, alert_threshold: parseFloat(e.target.value) })} /></div>
                    </div>
                    <div style={{ marginTop: 14 }}>
                        <label>Hukuk Alanları</label>
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                            {LEGAL_AREAS.map(la => (
                                <button key={la} type="button" onClick={() => toggleArea(la)}
                                    style={{
                                        padding: '4px 12px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
                                        background: form.legal_areas.includes(la) ? '#3B82F6' : '#273548',
                                        color: form.legal_areas.includes(la) ? '#fff' : '#94A3B8',
                                        border: `1px solid ${form.legal_areas.includes(la) ? '#3B82F6' : '#334155'}`,
                                    }}>{la}</button>
                            ))}
                        </div>
                    </div>
                    <div style={{ marginTop: 14 }}>
                        <label>Notlar</label>
                        <textarea value={form.notes} rows={2}
                            onChange={e => setForm({ ...form, notes: e.target.value })} />
                    </div>
                    <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
                        <button className="btn btn-primary" onClick={handleSave} disabled={saving || !form.client_name}>
                            {saving ? 'Kaydediliyor…' : 'Kaydet'}
                        </button>
                        <button className="btn btn-ghost" onClick={() => setShowForm(false)}>İptal</button>
                    </div>
                </div>
            )}

            {/* Table */}
            {loading ? <div className="spinner" /> : (
                <div className="card" style={{ overflowX: 'auto' }}>
                    {items.length === 0 ? (
                        <div className="empty-state">
                            <Users size={40} />
                            <p style={{ marginTop: 8 }}>Henüz müşteri eklenmemiş.</p>
                        </div>
                    ) : (
                        <table className="data-table">
                            <thead><tr>
                                <th>Müşteri</th><th>Şirket</th><th>Sektör</th>
                                <th>Hukuk Alanları</th><th>Eşik</th><th>Tarih</th><th></th>
                            </tr></thead>
                            <tbody>
                                {items.map(item => (
                                    <tr key={item.id}>
                                        <td style={{ fontWeight: 600, color: '#F1F5F9' }}>{item.client_name}</td>
                                        <td>{item.company_name}</td>
                                        <td><span style={{
                                            background: '#273548', padding: '2px 9px',
                                            borderRadius: 20, fontSize: 12, color: '#94A3B8'
                                        }}>{item.sector}</span></td>
                                        <td>{item.legal_areas?.slice(0, 3).map(la => (
                                            <span key={la} style={{
                                                background: 'rgba(59,130,246,0.12)', color: '#3B82F6',
                                                padding: '2px 7px', borderRadius: 12, fontSize: 11, marginRight: 4
                                            }}>{la}</span>
                                        ))}</td>
                                        <td>{Math.round(item.alert_threshold * 100)}%</td>
                                        <td style={{ fontSize: 12 }}>{format(new Date(item.created_at), 'dd.MM.yyyy')}</td>
                                        <td>
                                            <button className="btn btn-danger" style={{ padding: '5px 10px', fontSize: 12 }}
                                                onClick={() => handleDelete(item.id)}
                                                disabled={deletingId === item.id}>
                                                <Trash2 size={13} /> {deletingId === item.id ? '…' : 'Sil'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    );
};

export default Watchlist;
