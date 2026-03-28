import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

const api: AxiosInstance = axios.create({
    baseURL: BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token on every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('lexradar_token');
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auto-logout on 401
api.interceptors.response.use(
    (r) => r,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('lexradar_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

// ── Auth ────────────────────────────────────────────────────
export const login = async (username: string, password: string): Promise<string> => {
    const form = new URLSearchParams({ username, password });
    const res = await api.post('/api/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return res.data.access_token as string;
};

export const logout = () => api.post('/api/auth/logout');

// ── Reports ─────────────────────────────────────────────────
export interface FinalReport {
    doc_id: string;
    gazette_date: string;
    document_type: string;
    overall_signal: 'OPPORTUNITY' | 'RISK' | 'MIXED' | 'NEUTRAL' | '';
    confidence_score: number;
    executive_summary_en: string;
    executive_summary_tr: string;
    opportunities: Array<{ title: string; description: string; confidence: number }>;
    risks: Array<{ title: string; description: string; severity: string }>;
    decision_type: string;
    court_or_authority: string;
    legal_areas: string[];
    affected_sectors: string[];
    case_references: string[];
    key_entities: string[];
    urgency_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | '';
    action_required: boolean;
    recommended_actions: string[];
    source_url: string;
    source: string;
    processed_at: string;
}

export interface ReportStats {
    total_reports: number;
    risk_count: number;
    opportunity_count: number;
    mixed_count: number;
    neutral_count: number;
    by_source: Record<string, number>;
    by_legal_area: Record<string, number>;
    by_decision_type: Record<string, number>;
    last_run: string | null;
}

export const fetchReports = async (params?: {
    source?: string;
    days?: number;
    signal?: string;
    limit?: number;
}): Promise<FinalReport[]> => {
    const res = await api.get('/api/reports', { params });
    return res.data;
};

export const fetchReportStats = async (days = 30): Promise<ReportStats> => {
    const res = await api.get('/api/reports/stats', { params: { days } });
    return res.data;
};

export const fetchReport = async (docId: string): Promise<FinalReport> => {
    const res = await api.get(`/api/reports/${docId}`);
    return res.data;
};

// ── Watchlist ────────────────────────────────────────────────
export interface WatchlistItem {
    id: string;
    client_name: string;
    company_name: string;
    sector: string;
    legal_areas: string[];
    case_references: string[];
    watchlist_keywords: string[];
    alert_threshold: number;
    notes: string;
    created_at: string;
}

export const fetchWatchlist = async (): Promise<WatchlistItem[]> => {
    const res = await api.get('/api/watchlist');
    return res.data;
};

export const addWatchlistItem = async (item: Omit<WatchlistItem, 'id' | 'created_at'>): Promise<WatchlistItem> => {
    const res = await api.post('/api/watchlist', item);
    return res.data;
};

export const deleteWatchlistItem = async (id: string): Promise<void> => {
    await api.delete(`/api/watchlist/${id}`);
};

// ── Alerts ───────────────────────────────────────────────────
export const fetchAlerts = async (limit = 50): Promise<any[]> => {
    const res = await api.get('/api/alerts', { params: { limit } });
    return res.data;
};

// ── Pipeline ─────────────────────────────────────────────────
export const triggerPipeline = async (days_back = 1): Promise<{ status: string; run_id: string }> => {
    const res = await api.post('/api/pipeline/run', null, { params: { days_back } });
    return res.data;
};

export const fetchPipelineStatus = async (): Promise<any> => {
    const res = await api.get('/api/pipeline/status');
    return res.data;
};

export default api;
