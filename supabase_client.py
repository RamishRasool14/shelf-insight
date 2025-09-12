"""
Supabase client helper for persisting and fetching OSA analysis runs.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import os

from supabase import create_client, Client

from config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_TABLE_OSA_RUNS,
)


_client: Optional[Client] = None


def get_client() -> Optional[Client]:
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return _client
    except Exception:
        return None


def ensure_tables() -> None:
    """No-op placeholder: Supabase-managed schema; document in README."""
    return


def save_osa_run(
    *,
    date_str: str,
    display_id: str,
    ground_truth_skus: List[str],
    predicted_skus: List[str],
    accuracy_metrics: Dict[str, Any],
    raw_detection: Dict[str, Any],
    image_url: Optional[str],
) -> Tuple[bool, Optional[str]]:
    client = get_client()
    if client is None:
        return False, "Supabase client not configured"
    try:
        now_iso = datetime.utcnow().isoformat()
        payload = {
            "date": date_str,
            "display_id": display_id,
            "ground_truth_skus": ground_truth_skus,
            "predicted_skus": predicted_skus,
            "accuracy": accuracy_metrics.get("accuracy"),
            "metrics": accuracy_metrics,
            "raw_detection": raw_detection,
            "image_url": image_url,
            "created_at": now_iso,
        }
        client.table(SUPABASE_TABLE_OSA_RUNS).insert(payload).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def fetch_runs(
    *, date_str: Optional[str] = None, display_id: Optional[str] = None, limit: int = 50
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    client = get_client()
    if client is None:
        return [], "Supabase client not configured"
    try:
        q = client.table(SUPABASE_TABLE_OSA_RUNS).select("*")
        if date_str:
            q = q.eq("date", date_str)
        if display_id:
            q = q.eq("display_id", display_id)
        q = q.order("created_at", desc=True).limit(limit)
        res = q.execute()
        data = res.data or []
        return data, None
    except Exception as e:
        return [], str(e)


def fetch_run_by_index(
    *, date_str: str, display_id: str, index_from_latest: int
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    runs, err = fetch_runs(date_str=date_str, display_id=display_id, limit=100)
    if err:
        return None, err
    if not runs:
        return None, None
    if index_from_latest < 0 or index_from_latest >= len(runs):
        return None, None
    return runs[index_from_latest], None


