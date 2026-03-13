"""AI DevOps Incident Copilot - FastAPI Application.

Main entry point for the web API that orchestrates:
- Log simulation and ingestion
- Anomaly detection
- LLM-powered root cause analysis
- Automated GitHub issue creation
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.database import init_db
from src.incident_manager.manager import IncidentManager
from src.models import IncidentResponse, PipelineStatus

# ─────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────
settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Singleton incident manager
# ─────────────────────────────────────────────
incident_manager = IncidentManager()


# ─────────────────────────────────────────────
# Application Lifecycle
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("AI DevOps Incident Copilot - Starting Up")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Log configuration
    logger.info(f"LLM Mode: {'Mock (template-based)' if settings.llm_mock_mode else f'Ollama ({settings.ollama_model})'}")
    logger.info(f"GitHub: {'Dry Run' if settings.github_dry_run else 'Live'}")
    logger.info(f"Simulator: {'Enabled' if settings.simulator_enabled else 'Disabled'}")
    logger.info(f"Scan Interval: {settings.scan_interval}s")

    # Auto-start pipeline
    await incident_manager.start_pipeline()
    logger.info("Pipeline started - monitoring for anomalies...")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Shutting down pipeline...")
    await incident_manager.stop_pipeline()
    logger.info("Pipeline stopped. Goodbye!")


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(
    title="AI DevOps Incident Copilot",
    description=(
        "An AI-powered assistant that analyzes production incidents from K8s logs, "
        "detects anomalies, generates root cause analysis using LLMs, and automatically "
        "creates GitHub issues with detailed incident reports."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "AI DevOps Incident Copilot",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "pipeline_status": "/api/v1/status",
            "incidents": "/api/v1/incidents",
            "trigger_scan": "/api/v1/scan",
            "recent_logs": "/api/v1/logs",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ── Pipeline Status ──


@app.get("/api/v1/status", response_model=PipelineStatus, tags=["Pipeline"])
async def get_pipeline_status():
    """Get the current status of the incident detection pipeline."""
    return incident_manager.get_status()


@app.post("/api/v1/pipeline/start", tags=["Pipeline"])
async def start_pipeline():
    """Start the incident detection pipeline."""
    if incident_manager.is_running:
        return {"message": "Pipeline is already running"}
    await incident_manager.start_pipeline()
    return {"message": "Pipeline started successfully"}


@app.post("/api/v1/pipeline/stop", tags=["Pipeline"])
async def stop_pipeline():
    """Stop the incident detection pipeline."""
    if not incident_manager.is_running:
        return {"message": "Pipeline is not running"}
    await incident_manager.stop_pipeline()
    return {"message": "Pipeline stopped successfully"}


# ── Manual Scan ──


@app.post("/api/v1/scan", tags=["Detection"])
async def trigger_manual_scan():
    """Trigger a manual anomaly scan.

    This generates a batch of logs with a high probability of containing an anomaly,
    analyzes them, generates an RCA, and creates a GitHub issue.

    Perfect for demo purposes!
    """
    logger.info("Manual scan triggered via API")
    results = await incident_manager.trigger_manual_scan()

    if not results:
        return {
            "message": "Scan completed but no anomalies were detected in this batch. Try again!",
            "incidents": [],
        }

    return {
        "message": f"Scan completed. {len(results)} incident(s) detected and reported.",
        "incidents": results,
    }


# ── Incidents ──


@app.get("/api/v1/incidents", tags=["Incidents"])
async def list_incidents(
    limit: int = Query(default=50, ge=1, le=200, description="Max incidents to return"),
    severity: str | None = Query(default=None, description="Filter by severity: critical/high/medium/low"),
    status: str | None = Query(default=None, description="Filter by status: open/investigating/resolved"),
):
    """List all detected incidents, newest first."""
    incidents = incident_manager.get_incidents(limit=limit, severity=severity, status=status)

    return {
        "total": len(incidents),
        "incidents": [
            {
                "id": inc.id,
                "title": inc.title,
                "severity": inc.severity.value if inc.severity else "unknown",
                "status": inc.status.value if inc.status else "unknown",
                "service_name": inc.service_name,
                "anomaly_type": inc.anomaly_type,
                "summary": inc.llm_summary,
                "github_issue_url": inc.github_issue_url,
                "confidence_score": inc.confidence_score,
                "detected_at": inc.detected_at.isoformat() if inc.detected_at else None,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
            }
            for inc in incidents
        ],
    }


@app.get("/api/v1/incidents/{incident_id}", tags=["Incidents"])
async def get_incident(incident_id: int):
    """Get detailed information about a specific incident."""
    incident = incident_manager.get_incident_by_id(incident_id)

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident #{incident_id} not found")

    return {
        "id": incident.id,
        "title": incident.title,
        "severity": incident.severity.value if incident.severity else "unknown",
        "status": incident.status.value if incident.status else "unknown",
        "service_name": incident.service_name,
        "anomaly_type": incident.anomaly_type,
        "raw_logs": incident.raw_logs,
        "root_cause_analysis": incident.root_cause_analysis,
        "suggested_fixes": incident.suggested_fixes,
        "llm_summary": incident.llm_summary,
        "github_issue_url": incident.github_issue_url,
        "confidence_score": incident.confidence_score,
        "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


# ── Logs ──


@app.get("/api/v1/logs", tags=["Logs"])
async def get_recent_logs(
    count: int = Query(default=50, ge=1, le=500, description="Number of recent logs"),
):
    """Get recent logs from the simulator buffer."""
    logs = incident_manager.simulator.get_recent_logs(count=count)

    return {
        "total": len(logs),
        "total_generated": incident_manager.simulator.total_generated,
        "anomalies_injected": incident_manager.simulator.anomalies_injected,
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "namespace": log.namespace,
                "pod_name": log.pod_name,
                "container_name": log.container_name,
                "log_level": log.log_level,
                "message": log.message,
                "metadata": log.metadata,
            }
            for log in logs
        ],
    }


@app.delete("/api/v1/logs", tags=["Logs"])
async def clear_log_buffer():
    """Clear the log buffer."""
    cleared = incident_manager.simulator.clear_buffer()
    return {"message": f"Cleared {cleared} logs from buffer"}


# ── Detector Stats ──


@app.get("/api/v1/detector/stats", tags=["Detection"])
async def get_detector_stats():
    """Get anomaly detector statistics."""
    return incident_manager.detector.get_stats()
