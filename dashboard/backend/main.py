"""
LexRadar Dashboard — FastAPI Backend

Endpoints:
  POST /api/auth/login                    — JWT login
  POST /api/auth/logout                   — logout (client-side token drop)
  GET  /api/reports                        — list FinalReports
  GET  /api/reports/stats                  — aggregate statistics
  GET  /api/reports/{doc_id}               — single report
  GET  /api/watchlist                      — list ClientWatchlist items
  POST /api/watchlist                      — add new item
  DELETE /api/watchlist/{id}              — remove item
  GET  /api/alerts                         — last 50 alert log lines
  POST /api/pipeline/run                  — trigger main.py run-now
  GET  /api/pipeline/status               — latest pipeline run
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration — read from environment, fall back to dev defaults
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]   # LexRadar/
REPORTS_DIR = BASE_DIR / "data" / "intelligence_reports"
ALERT_LOG_FILE = BASE_DIR / "data" / "alert_log.jsonl"
PIPELINE_LOG_FILE = BASE_DIR / "data" / "pipeline_runs.jsonl"
WATCHLIST_FILE = BASE_DIR / "data" / "watchlist.jsonl"

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lexradar-super-secret-dev-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 h

# Single admin user — set DASHBOARD_EMAIL and DASHBOARD_PASSWORD in .env for production
ADMIN_EMAIL = os.getenv("DASHBOARD_EMAIL", "admin@lexradar.com")
ADMIN_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "lexradar2024")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _verify_password(plain: str) -> bool:
    return plain == ADMIN_PASSWORD


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc
    return email


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class WatchlistItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    company_name: str
    sector: Literal["TEKNOLOJI", "FINANS", "INSAAT", "ILAC", "ENERJI", "DIGER"]
    legal_areas: List[str] = Field(default_factory=list)
    case_references: List[str] = Field(default_factory=list)
    watchlist_keywords: List[str] = Field(default_factory=list)
    alert_threshold: float = 0.75
    notes: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PipelineRunResponse(BaseModel):
    status: str
    run_id: str


class ReportStats(BaseModel):
    total_reports: int
    risk_count: int
    opportunity_count: int
    mixed_count: int
    neutral_count: int
    by_source: Dict[str, int]
    by_legal_area: Dict[str, int]
    by_decision_type: Dict[str, int]
    last_run: Optional[str]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_reports(
    source_filter: Optional[str] = None,
    days: int = 7,
    signal_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read all JSON reports from REPORTS_DIR, apply filters, sort by date desc."""
    if not REPORTS_DIR.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results: List[Dict[str, Any]] = []

    for fp in REPORTS_DIR.glob("*.json"):
        try:
            data: Dict[str, Any] = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Date filter
        processed_at_raw = data.get("processed_at", "")
        try:
            processed_at = datetime.fromisoformat(processed_at_raw)
            if processed_at.tzinfo is None:
                processed_at = processed_at.replace(tzinfo=timezone.utc)
            if processed_at < cutoff:
                continue
        except (ValueError, TypeError):
            pass  # Include reports with missing/invalid dates

        # Source filter
        if source_filter and data.get("source", "").upper() != source_filter.upper():
            continue

        # Signal filter
        if signal_filter and data.get("overall_signal", "").upper() != signal_filter.upper():
            continue

        results.append(data)

    results.sort(key=lambda r: r.get("processed_at", ""), reverse=True)
    return results


def _load_report_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    if not REPORTS_DIR.exists():
        return None
    for fp in REPORTS_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("doc_id") == doc_id:
                return data
        except Exception:
            continue
    return None


def _load_watchlist() -> List[Dict[str, Any]]:
    if not WATCHLIST_FILE.exists():
        return []
    items = []
    for line in WATCHLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def _save_watchlist(items: List[Dict[str, Any]]) -> None:
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with WATCHLIST_FILE.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _load_alert_log(limit: int = 50) -> List[Dict[str, Any]]:
    if not ALERT_LOG_FILE.exists():
        return []
    lines = [l.strip() for l in ALERT_LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    recent = lines[-limit:]
    alerts = []
    for line in reversed(recent):
        try:
            alerts.append(json.loads(line))
        except Exception:
            alerts.append({"raw": line})
    return alerts


def _load_pipeline_status() -> Optional[Dict[str, Any]]:
    if not PIPELINE_LOG_FILE.exists():
        return None
    lines = [l.strip() for l in PIPELINE_LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return {"raw": lines[-1]}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LexRadar Dashboard API",
    description="Backend API for the Legal Intelligence Radar dashboard.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_ORIGIN", "https://lexradar.com"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """Password login — returns JWT access token."""
    if form.username != ADMIN_EMAIL or not _verify_password(form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_access_token(
        {"sub": form.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


@app.post("/api/auth/logout", tags=["Auth"])
async def logout(_: str = Depends(_get_current_user)) -> Dict[str, str]:
    """Logout — instructs client to drop the token. Server is stateless."""
    return {"message": "Logged out successfully. Please discard your token."}


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

@app.get("/api/reports/stats", response_model=ReportStats, tags=["Reports"])
async def get_report_stats(
    days: int = Query(default=30, ge=1, le=365),
    _: str = Depends(_get_current_user),
) -> ReportStats:
    """Return aggregate statistics over the last N days."""
    reports = _load_reports(days=days)
    signal_counter: Counter = Counter()
    source_counter: Counter = Counter()
    legal_area_counter: Counter = Counter()
    decision_type_counter: Counter = Counter()

    for r in reports:
        signal_counter[r.get("overall_signal", "NEUTRAL")] += 1
        src = r.get("source") or "UNKNOWN"
        source_counter[src.upper()] += 1
        for la in r.get("legal_areas", []):
            legal_area_counter[la] += 1
        dt = r.get("decision_type") or "OTHER"
        decision_type_counter[dt] += 1

    pipeline_status = _load_pipeline_status()
    last_run = pipeline_status.get("started_at") if pipeline_status else None

    return ReportStats(
        total_reports=len(reports),
        risk_count=signal_counter.get("RISK", 0),
        opportunity_count=signal_counter.get("OPPORTUNITY", 0),
        mixed_count=signal_counter.get("MIXED", 0),
        neutral_count=signal_counter.get("NEUTRAL", 0),
        by_source=dict(source_counter),
        by_legal_area=dict(legal_area_counter),
        by_decision_type=dict(decision_type_counter),
        last_run=last_run,
    )


@app.get("/api/reports", tags=["Reports"])
async def list_reports(
    source: Optional[str] = Query(default=None, description="GAZETTE|YARGITAY|DANISTAY|KIK"),
    days: int = Query(default=7, ge=1, le=365),
    signal: Optional[str] = Query(default=None, description="RISK|OPPORTUNITY|MIXED|NEUTRAL"),
    limit: int = Query(default=100, ge=1, le=500),
    _: str = Depends(_get_current_user),
) -> List[Dict[str, Any]]:
    """List intelligence reports sorted by processed_at DESC."""
    reports = _load_reports(source_filter=source, days=days, signal_filter=signal)
    return reports[:limit]


@app.get("/api/reports/{doc_id}", tags=["Reports"])
async def get_report(
    doc_id: str,
    _: str = Depends(_get_current_user),
) -> Dict[str, Any]:
    """Return a single intelligence report by doc_id."""
    report = _load_report_by_id(doc_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{doc_id}' not found.")
    return report


# ---------------------------------------------------------------------------
# WATCHLIST
# ---------------------------------------------------------------------------

@app.get("/api/watchlist", tags=["Watchlist"])
async def get_watchlist(
    _: str = Depends(_get_current_user),
) -> List[Dict[str, Any]]:
    """Return all client watchlist items."""
    return _load_watchlist()


@app.post("/api/watchlist", status_code=status.HTTP_201_CREATED, tags=["Watchlist"])
async def add_watchlist_item(
    item: WatchlistItem,
    _: str = Depends(_get_current_user),
) -> Dict[str, Any]:
    """Add a new watchlist item."""
    items = _load_watchlist()
    new_item = item.model_dump()
    items.append(new_item)
    _save_watchlist(items)
    return new_item


@app.delete("/api/watchlist/{item_id}", tags=["Watchlist"])
async def delete_watchlist_item(
    item_id: str,
    _: str = Depends(_get_current_user),
) -> Dict[str, str]:
    """Remove a watchlist item by id."""
    items = _load_watchlist()
    updated = [i for i in items if str(i.get("id")) != item_id]
    if len(updated) == len(items):
        raise HTTPException(status_code=404, detail=f"Watchlist item '{item_id}' not found.")
    _save_watchlist(updated)
    return {"message": f"Watchlist item '{item_id}' deleted."}


# ---------------------------------------------------------------------------
# ALERTS
# ---------------------------------------------------------------------------

@app.get("/api/alerts", tags=["Alerts"])
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    _: str = Depends(_get_current_user),
) -> List[Dict[str, Any]]:
    """Return the last N alert log entries (newest first)."""
    return _load_alert_log(limit=limit)


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/run", response_model=PipelineRunResponse, tags=["Pipeline"])
async def trigger_pipeline(
    days_back: int = Query(default=1, ge=1, le=30),
    _: str = Depends(_get_current_user),
) -> PipelineRunResponse:
    """
    Trigger a pipeline run asynchronously.
    Executes: python main.py run-now --days-back <N>
    """
    run_id = str(uuid.uuid4())

    python_exe = sys.executable
    cmd = [python_exe, str(BASE_DIR / "main.py"), "run-now", "--days-back", str(days_back)]

    # Fire-and-forget in background — does not block the response
    try:
        subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to launch pipeline: {exc}",
        )

    return PipelineRunResponse(status="started", run_id=run_id)


@app.get("/api/pipeline/status", tags=["Pipeline"])
async def get_pipeline_status(
    _: str = Depends(_get_current_user),
) -> Dict[str, Any]:
    """Return the last entry from pipeline_runs.jsonl."""
    status_data = _load_pipeline_status()
    if status_data is None:
        return {"message": "No pipeline runs recorded yet."}
    return status_data


# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
async def health() -> Dict[str, str]:
    """Public health check endpoint."""
    return {
        "status": "ok",
        "service": "LexRadar Dashboard API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Entrypoint (uvicorn)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "dashboard.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
