"""Data Source Control Plane & RunContext Endpoints for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pathlib import Path
import tempfile
import shutil

from backend.app.connectors.provider_registry import ProviderRegistry
from backend.app.core.deps import get_run_context_manager
from backend.app.core.state import RunContextManager
from backend.app.ingestion.csv_normalizer import CSVDatasetPreview, CSVNormalizer
from backend.app.models.run_context import (
    DataSourceType,
    ReplayControlRequest,
    RunContext,
    RunMode,
    RunStatus,
    SourceSelectRequest,
)

router = APIRouter(prefix="/runtime", tags=["Runtime & Data Source Control Plane"])

# In-memory run history log for audit trail
_RUN_HISTORY: List[Dict[str, Any]] = []


@router.get("/context", response_model=RunContext)
async def get_active_run_context(
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> RunContext:
    """Get canonical active RunContext detailing current data source, run mode, transport, and execution status."""
    return ctx_mgr.get_context()


@router.get("/providers")
async def list_data_source_providers() -> List[Dict[str, Any]]:
    """List available data source providers, configuration state, default modes, and descriptions."""
    return ProviderRegistry.list_providers()


@router.post("/source/select", response_model=RunContext)
async def select_data_source(
    payload: SourceSelectRequest,
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> RunContext:
    """Switch active data source and run mode.
    
    Resets transient source state, generates a fresh run_id, and updates canonical RunContext.
    """
    try:
        current = ctx_mgr.get_context()
        # Record finished run in history if active
        if current.run_id and current.status != RunStatus.IDLE:
            _RUN_HISTORY.append({
                "run_id": current.run_id,
                "source_type": current.source_type,
                "source_name": current.source_name,
                "mode": current.mode,
                "dataset_id": current.dataset_id,
                "station_count": current.station_count,
                "observation_count": current.observation_count,
                "created_at": current.created_at.isoformat(),
                "status": current.status,
            })

        new_ctx = ctx_mgr.select_source(
            source_type=payload.source_type,
            mode=payload.mode,
            dataset_id=payload.dataset_id,
            config=payload.config,
        )
        return new_ctx
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to select data source: {exc}")


@router.post("/run/start", response_model=RunContext)
async def start_active_run(
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> RunContext:
    """Start or resume execution of current RunContext."""
    return ctx_mgr.update_context(status=RunStatus.RUNNING)


@router.post("/run/pause", response_model=RunContext)
async def pause_active_run(
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> RunContext:
    """Pause execution of current RunContext."""
    return ctx_mgr.update_context(status=RunStatus.PAUSED)


@router.post("/run/reset", response_model=RunContext)
async def reset_active_run(
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> RunContext:
    """Reset current RunContext state pointers to initial conditions without destructive database operations."""
    return ctx_mgr.update_context(
        status=RunStatus.IDLE,
        current_observation_index=0,
        current_synthetic_time=None,
    )


@router.post("/csv/preview", response_model=CSVDatasetPreview)
async def preview_csv_dataset(
    file: UploadFile = File(...),
) -> CSVDatasetPreview:
    """Upload and analyze historical CSV dataset to generate column mapping, missingness, and preview before execution."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only CSV files are supported.")

    try:
        # Save temporary file for preview analysis
        temp_dir = Path(tempfile.gettempdir()) / "skyguard_csv_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        preview = CSVNormalizer.generate_preview(temp_path)
        return preview
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV Preview Generation failed: {exc}")


@router.get("/history")
async def get_run_history(
    ctx_mgr: RunContextManager = Depends(get_run_context_manager),
) -> List[Dict[str, Any]]:
    """Get audit history log of previous execution runs."""
    history = list(_RUN_HISTORY)
    current = ctx_mgr.get_context()
    # Include active run if initialized
    history.append({
        "run_id": current.run_id,
        "source_type": current.source_type,
        "source_name": current.source_name,
        "mode": current.mode,
        "dataset_id": current.dataset_id,
        "station_count": current.station_count,
        "observation_count": current.observation_count,
        "created_at": current.created_at.isoformat(),
        "status": current.status,
    })
    return history
