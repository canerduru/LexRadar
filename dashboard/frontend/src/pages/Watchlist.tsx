import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Users, RefreshCw, X } from 'lucide-react';
import { fetchWatchlist, addWatchlistItem, deleteWatchlistItem, WatchlistItem } from '../services/api';

const SECTORS = ['TEKNOLOJI', 'FINANS', 'INSAAT', 'ILAC', 'ENERJI', 'DIGER'];
const LEGAL_AREAS = ['REKABET', 'VERGI', 'IS_HUKUKU', 'KVKK', 'IHALE', 'SIRKETLER', 'CEZA', 'IDARE'];

const blankForm = (): Omit<WatchlistItem, 'id' | 'created_at'> => ({
    client_name: '', company_name: '', sector: 'TEKNOLOJI',
    legal_areas: [], case_references: [], watchlist_keywords: [],
    alert_threshold: 0.75, notes: '',
});

const Watchlist: React.FC = () => {
    const [items, setItems] = useState<WatchlistItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form, setForm] = useState(blankForm());
    const [keywordInput, setKeywordInput] = useState('');
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        try { setItems(await fetchWatchlist()); } finally { setLoading(false); }
    };
    useEffect(() => { load(); }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.client_name || !form.company_name) return;
        setSaving(true);
        try {
            const added = await addWatchlistItem(form);
            setItems(prev => [added, ...prev]);
            setIsModalOpen(false);
            setForm(blankForm());
        } finally { setSaving(false); }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!window.confirm(`'${name}' müşterisini izleme listesinden silmek istediğinize emin misiniz?`)) return;
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

    const handleKeywordKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const kw = keywordInput.trim();
            if (kw && !form.watchlist_keywords.includes(kw)) {
                setForm(f => ({ ...f, watchlist_keywords: [...f.watchlist_keywords, kw] }));
                setKeywordInput('');
            }
        }
    };

    const removeKeyword = (kw: string) => {
        setForm(f => ({ ...f, watchlist_keywords: f.watchlist_keywords.filter(k => k !== kw) }));
    };

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">Müşteri Takip Listesi</div>
                    <div className="page-subtitle">{items.length} müşteri takip ediliyor</div>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <button className="btn btn-ghost" onClick={load}><RefreshCw size={15} /> Yenile</button>
                    <button className="btn btn-primary" onClick={() => { setForm(blankForm()); setIsModalOpen(true); }}>
                        <Plus size={16} /> Yeni Ekle
                    </button>
                </div>
            </div>

            {/* Table */}
            {loading ? <div className="spinner" /> : (
                <div className="card" style={{ overflowX: 'auto' }}>
                    {items.length === 0 ? (
                        <div className="empty-state">
                            <Users size={44} style={{ color: '#475569' }} />
                            <p style={{ marginTop: 12, fontSize: 15, color: '#94A3B8' }}>Listenizde henüz kayıtlı müşteri yok.</p>
                            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setIsModalOpen(true)}>
                                İlk Müşteriyi Ekle
                            </button>
                        </div>
                    ) : (
                        <table className="data-table" style={{ width: '100%', textAlign: 'left' }}>
                            <thead>
                                <tr>
                                    <th>Müşteri</th>
                                    <th>Şirket</th>
                                    <th>Sektör</th>
                                    <th>Hukuki Alanlar</th>
                                    <th>Anahtar Kelimeler</th>
                                    <th style={{ textAlign: 'right' }}>İşlemler</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items.map(item => (
                                    <tr key={item.id}>
                                        <td style={{ fontWeight: 600, color: '#F1F5F9', padding: '14px 16px' }}>{item.client_name}</td>
                                        <td style={{ padding: '14px 16px', color: '#CBD5E1' }}>{item.company_name}</td>
                                        <td style={{ padding: '14px 16px' }}>
                                            <span style={{ background: '#1E293B', border: '1px solid #334155', padding: '3px 10px', borderRadius: 20, fontSize: 12, color: '#94A3B8' }}>
                                                {item.sector}
                                            </span>
                                        </td>
                                        <td style={{ padding: '14px 16px', maxWidth: 200 }}>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                                {item.legal_areas?.map(la => (
                                                    <span key={la} style={{ background: 'rgba(59,130,246,0.15)', color: '#60A5FA', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>
                                                        {la}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td style={{ padding: '14px 16px', maxWidth: 200 }}>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                                {item.watchlist_keywords?.map(kw => (
                                                    <span key={kw} style={{ background: '#1E293B', color: '#94A3B8', border: '1px solid #334155', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>
                                                        {kw}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                                            <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 13, color: '#EF4444', borderColor: 'transparent' }}
                                                onClick={() => handleDelete(item.id, item.client_name)}
                                                disabled={deletingId === item.id}>
                                                <Trash2 size={15} /> {deletingId === item.id ? 'Siliniyor...' : 'Sil'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Modal Overlay */}
            {isModalOpen && (
                <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(4px)' }}>
                    <div className="card" style={{ width: '100%', maxWidth: 540, background: '#1E293B', padding: 0, border: '1px solid #334155', overflow: 'hidden' }}>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #334155' }}>
                            <h2 style={{ fontSize: 18, fontWeight: 600, color: '#F1F5F9', margin: 0 }}>Müşteri Ekle</h2>
                            <button style={{ background: 'none', border: 'none', color: '#64748B', cursor: 'pointer' }} onClick={() => setIsModalOpen(false)}>
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleSave} style={{ padding: '24px', maxHeight: '75vh', overflowY: 'auto' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                                <div>
                                    <label>Müşteri Adı *</label>
                                    <input required value={form.client_name} onChange={e => setForm({ ...form, client_name: e.target.value })} placeholder="Örn: Ahmet Yılmaz" />
                                </div>
                                <div>
                                    <label>Şirket Adı *</label>
                                    <input required value={form.company_name} onChange={e => setForm({ ...form, company_name: e.target.value })} placeholder="Örn: ACME A.Ş." />
                                </div>
                            </div>

                            <div style={{ marginBottom: 20 }}>
                                <label>Sektör</label>
                                <select value={form.sector} onChange={e => setForm({ ...form, sector: e.target.value as any })}>
                                    {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                            </div>

                            <div style={{ marginBottom: 20 }}>
                                <label>Hukuki Alanlar</label>
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                                    {LEGAL_AREAS.map(la => {
                                        const active = form.legal_areas.includes(la);
                                        return (
                                            <button key={la} type="button" onClick={() => toggleArea(la)}
                                                style={{
                                                    padding: '6px 12px', borderRadius: 20, fontSize: 12, cursor: 'pointer', fontWeight: 500,
                                                    background: active ? '#3B82F6' : '#273548',
                                                    color: active ? '#fff' : '#94A3B8',
                                                    border: `1px solid ${active ? '#3B82F6' : '#334155'}`,
                                                    transition: 'all 150ms'
                                                }}>
                                                {la}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div style={{ marginBottom: 20 }}>
                                <label>Anahtar Kelimeler (Enter ile ekleyin)</label>
                                <div style={{
                                    display: 'flex', flexWrap: 'wrap', gap: 8, padding: '8px',
                                    background: '#273548', border: '1px solid #334155', borderRadius: 6, minHeight: 42
                                }}>
                                    {form.watchlist_keywords.map(kw => (
                                        <span key={kw} style={{
                                            background: '#1E293B', border: '1px solid #3E4F66', padding: '4px 10px',
                                            borderRadius: 16, fontSize: 13, color: '#F1F5F9', display: 'flex', alignItems: 'center', gap: 6
                                        }}>
                                            {kw}
                                            <X size={12} color="#94A3B8" style={{ cursor: 'pointer' }} onClick={() => removeKeyword(kw)} />
                                        </span>
                                    ))}
                                    <input
                                        type="text"
                                        value={keywordInput}
                                        onChange={e => setKeywordInput(e.target.value)}
                                        onKeyDown={handleKeywordKeyDown}
                                        placeholder="Kelime yazın..."
                                        style={{ flex: 1, minWidth: 120, border: 'none', background: 'transparent', padding: '4px', fontSize: 14 }}
                                    />
                                </div>
                            </div>

                            <div style={{ marginBottom: 20 }}>
                                <label>Notlar</label>
                                <textarea rows={3} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Ek bilgiler..." />
                            </div>

                            <div style={{ marginBottom: 32 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <label style={{ margin: 0 }}>Alert Eşiği</label>
                                    <span style={{ fontSize: 13, color: '#3B82F6', fontWeight: 600 }}>%{Math.round(form.alert_threshold * 100)} Minimum Eşleşme</span>
                                </div>
                                <input type="range" min={0.5} max={1.0} step={0.05}
                                    value={form.alert_threshold}
                                    onChange={e => setForm({ ...form, alert_threshold: parseFloat(e.target.value) })}
                                    style={{ width: '100%', cursor: 'pointer', accentColor: '#3B82F6' }}
                                />
                            </div>

                            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', borderTop: '1px solid #334155', paddingTop: 20 }}>
                                <button type="button" className="btn btn-ghost" onClick={() => setIsModalOpen(false)}>İptal</button>
                                <button type="submit" className="btn btn-primary" disabled={saving || !form.client_name}>
                                    {saving ? 'Kaydediliyor...' : 'Kaydet'}
                                </button>
                            </div>
                        </form>

                    </div>
                </div>
            )}
        </div>
    );
};

export default Watchlist;
