"""Incident Manager - Orchestrates the full detection-analysis-reporting pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_session_factory
from src.models import (
    AnomalyEvent,
    IncidentCreate,
    IncidentRecord,
    IncidentResponse,
    IncidentStatus,
    PipelineStatus,
)
from src.log_simulator.simulator import LogSimulator
from src.anomaly_detector.detector import AnomalyDetector
from src.llm_analyzer.analyzer import LLMAnalyzer
from src.github_integration.client import GitHubClient

logger = logging.getLogger(__name__)


class IncidentManager:
    """Orchestrates the end-to-end incident detection and response pipeline.

    Pipeline:
    1. Log Simulator generates logs (or real logs are ingested)
    2. Anomaly Detector scans logs for anomalies
    3. LLM Analyzer generates Root Cause Analysis
    4. GitHub integration creates incident issues
    5. Incidents are stored in the database
    """

    def __init__(self):
        settings = get_settings()

        # Initialize components
        self.simulator = LogSimulator(anomaly_probability=0.08)
        self.detector = AnomalyDetector(z_score_threshold=2.5)
        self.analyzer = LLMAnalyzer()
        self.github_client = GitHubClient()

        # Pipeline state
        self._running = False
        self._simulator_task: asyncio.Task | None = None
        self._detector_task: asyncio.Task | None = None
        self._total_incidents = 0
        self._last_scan_at: datetime | None = None

        # Settings
        self._scan_interval = settings.scan_interval
        self._simulator_interval = settings.simulator_interval
        self._simulator_batch_size = settings.simulator_batch_size
        self._simulator_enabled = settings.simulator_enabled

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> PipelineStatus:
        """Get current pipeline status."""
        return PipelineStatus(
            simulator_running=self._simulator_task is not None
            and not self._simulator_task.done(),
            detector_running=self._detector_task is not None
            and not self._detector_task.done(),
            total_logs_processed=self.detector.total_logs_analyzed,
            total_anomalies_detected=self.detector.total_anomalies_detected,
            total_incidents_created=self._total_incidents,
            last_scan_at=self._last_scan_at,
        )

    async def start_pipeline(self):
        """Start the full incident detection pipeline."""
        if self._running:
            logger.warning("Pipeline is already running")
            return

        self._running = True
        logger.info("Starting incident detection pipeline...")

        # Start log simulator
        if self._simulator_enabled:
            self._simulator_task = asyncio.create_task(
                self.simulator.run_continuous(
                    interval=self._simulator_interval,
                    batch_size=self._simulator_batch_size,
                )
            )
            logger.info("Log simulator started")

        # Start anomaly detection loop
        self._detector_task = asyncio.create_task(self._detection_loop())
        logger.info("Anomaly detection loop started")

    async def stop_pipeline(self):
        """Stop the pipeline gracefully."""
        self._running = False
        self.simulator.stop()

        if self._simulator_task:
            self._simulator_task.cancel()
            try:
                await self._simulator_task
            except asyncio.CancelledError:
                pass

        if self._detector_task:
            self._detector_task.cancel()
            try:
                await self._detector_task
            except asyncio.CancelledError:
                pass

        logger.info("Pipeline stopped")

    async def _detection_loop(self):
        """Main detection loop that periodically scans for anomalies."""
        logger.info(f"Detection loop running (interval: {self._scan_interval}s)")

        while self._running:
            try:
                await self._run_detection_cycle()
            except Exception as e:
                logger.error(f"Error in detection cycle: {e}", exc_info=True)

            await asyncio.sleep(self._scan_interval)

    async def _run_detection_cycle(self):
        """Run a single detection cycle: scan → analyze → report."""
        self._last_scan_at = datetime.utcnow()

        # Get recent logs from simulator buffer
        logs = self.simulator.get_recent_logs(count=200)
        if not logs:
            return

        # Detect anomalies
        anomalies = self.detector.analyze_logs(logs)
        if not anomalies:
            return

        logger.info(f"Processing {len(anomalies)} detected anomaly/anomalies...")

        # Process each anomaly
        for anomaly in anomalies:
            await self._process_anomaly(anomaly)

    async def _process_anomaly(self, anomaly: AnomalyEvent):
        """Process a single anomaly: LLM analysis → GitHub issue → DB storage."""
        try:
            # Step 1: Generate RCA with LLM
            logger.info(f"Generating RCA for {anomaly.anomaly_type} on {anomaly.service_name}...")
            rca = await self.analyzer.analyze(anomaly)
            logger.info(f"RCA generated: {rca.incident_title}")

            # Step 2: Create GitHub issue
            logger.info("Creating GitHub issue...")
            issue_result = self.github_client.create_incident_issue(anomaly, rca)
            github_url = issue_result.get("url")
            logger.info(f"GitHub issue: {github_url}")

            # Step 3: Store in database
            incident = self._store_incident(anomaly, rca, github_url)
            self._total_incidents += 1
            logger.info(
                f"Incident #{incident.id} created: {rca.incident_title} "
                f"(severity: {anomaly.severity.value}, github: {github_url})"
            )

            # Log the full issue body for demo visibility
            logger.info(
                f"\n{'='*80}\n"
                f"INCIDENT REPORT #{incident.id}\n"
                f"{'='*80}\n"
                f"Title: {rca.incident_title}\n"
                f"Severity: {anomaly.severity.value.upper()}\n"
                f"Service: {anomaly.service_name}\n"
                f"Type: {anomaly.anomaly_type}\n"
                f"Confidence: {rca.confidence_score:.0%}\n"
                f"\nSummary: {rca.summary}\n"
                f"\nRoot Cause: {rca.root_cause[:200]}...\n"
                f"\nSuggested Fixes:\n" +
                "\n".join(f"  {i+1}. {fix}" for i, fix in enumerate(rca.suggested_fixes[:3])) +
                f"\n\nGitHub Issue: {github_url}\n"
                f"{'='*80}\n"
            )

        except Exception as e:
            logger.error(f"Failed to process anomaly: {e}", exc_info=True)

    def _store_incident(
        self,
        anomaly: AnomalyEvent,
        rca,
        github_url: str | None,
    ) -> IncidentRecord:
        """Store an incident in the database."""
        session_factory = get_session_factory()
        session = session_factory()

        try:
            # Format log snippets for storage
            log_text = ""
            if anomaly.related_logs:
                lines = []
                for log in anomaly.related_logs:
                    lines.append(
                        f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"[{log.log_level}] [{log.pod_name}] {log.message}"
                    )
                log_text = "\n".join(lines)

            incident = IncidentRecord(
                title=rca.incident_title,
                severity=anomaly.severity,
                status=IncidentStatus.OPEN,
                service_name=anomaly.service_name,
                anomaly_type=anomaly.anomaly_type,
                raw_logs=log_text,
                root_cause_analysis=rca.root_cause,
                suggested_fixes="\n".join(rca.suggested_fixes),
                llm_summary=rca.summary,
                github_issue_url=github_url,
                confidence_score=rca.confidence_score,
                detected_at=anomaly.detected_at,
            )

            session.add(incident)
            session.commit()
            session.refresh(incident)
            return incident

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store incident: {e}")
            raise
        finally:
            session.close()

    def get_incidents(
        self,
        limit: int = 50,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[IncidentRecord]:
        """Retrieve incidents from the database."""
        session_factory = get_session_factory()
        session = session_factory()

        try:
            query = session.query(IncidentRecord)

            if severity:
                query = query.filter(IncidentRecord.severity == severity)
            if status:
                query = query.filter(IncidentRecord.status == status)

            return (
                query.order_by(IncidentRecord.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def get_incident_by_id(self, incident_id: int) -> IncidentRecord | None:
        """Get a single incident by ID."""
        session_factory = get_session_factory()
        session = session_factory()

        try:
            return session.query(IncidentRecord).filter_by(id=incident_id).first()
        finally:
            session.close()

    async def trigger_manual_scan(self) -> list[dict]:
        """Trigger a manual scan and return detected anomalies with RCA."""
        results = []

        # Generate a batch with higher anomaly probability for demo
        original_prob = self.simulator.anomaly_probability
        self.simulator.anomaly_probability = 0.8  # High chance for demo
        logs = self.simulator.generate_batch(batch_size=15)
        self.simulator.anomaly_probability = original_prob

        # Detect anomalies
        anomalies = self.detector.analyze_logs(logs)

        for anomaly in anomalies:
            rca = await self.analyzer.analyze(anomaly)
            issue_result = self.github_client.create_incident_issue(anomaly, rca)
            incident = self._store_incident(anomaly, rca, issue_result.get("url"))
            self._total_incidents += 1

            results.append({
                "incident_id": incident.id,
                "title": rca.incident_title,
                "severity": anomaly.severity.value,
                "service": anomaly.service_name,
                "anomaly_type": anomaly.anomaly_type,
                "summary": rca.summary,
                "root_cause": rca.root_cause[:300],
                "suggested_fixes": rca.suggested_fixes[:3],
                "github_issue_url": issue_result.get("url"),
                "confidence": rca.confidence_score,
            })

        return results
