"""Main anomaly detection engine combining rule-based and statistical detection."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from src.models import AnomalyEvent, IncidentSeverity, LogEntry
from src.anomaly_detector.rules import RULES, DetectionRule
from src.anomaly_detector.statistical import StatisticalDetector

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Combined anomaly detection engine.

    Uses:
    1. Rule-based detection: Pattern matching on log messages.
    2. Statistical detection: Z-score analysis on error rates and log volumes.
    """

    def __init__(self, z_score_threshold: float = 2.5):
        self.statistical_detector = StatisticalDetector(
            z_score_threshold=z_score_threshold
        )
        self._total_logs_analyzed = 0
        self._total_anomalies_detected = 0
        # Track recently detected anomalies to avoid duplicates
        self._recent_anomalies: dict[str, datetime] = {}
        self._cooldown_seconds = 60  # Don't re-report same anomaly within this window

    @property
    def total_logs_analyzed(self) -> int:
        return self._total_logs_analyzed

    @property
    def total_anomalies_detected(self) -> int:
        return self._total_anomalies_detected

    def _is_on_cooldown(self, anomaly_key: str) -> bool:
        """Check if an anomaly type + service combo is on cooldown."""
        if anomaly_key in self._recent_anomalies:
            last_seen = self._recent_anomalies[anomaly_key]
            elapsed = (datetime.utcnow() - last_seen).total_seconds()
            if elapsed < self._cooldown_seconds:
                return True
        return False

    def _severity_from_string(self, severity_str: str) -> IncidentSeverity:
        """Convert severity string to enum."""
        mapping = {
            "critical": IncidentSeverity.CRITICAL,
            "high": IncidentSeverity.HIGH,
            "medium": IncidentSeverity.MEDIUM,
            "low": IncidentSeverity.LOW,
        }
        return mapping.get(severity_str.lower(), IncidentSeverity.MEDIUM)

    def analyze_logs(self, logs: list[LogEntry]) -> list[AnomalyEvent]:
        """Analyze a batch of logs for anomalies.

        Runs both rule-based and statistical detection.

        Args:
            logs: Batch of log entries to analyze.

        Returns:
            List of detected anomaly events.
        """
        if not logs:
            return []

        self._total_logs_analyzed += len(logs)

        # Update statistical metrics
        self.statistical_detector.update_metrics(logs)

        anomalies: list[AnomalyEvent] = []

        # ── Rule-based detection ──
        rule_anomalies = self._run_rule_detection(logs)
        anomalies.extend(rule_anomalies)

        # ── Statistical detection ──
        stat_anomalies = self._run_statistical_detection(logs)
        anomalies.extend(stat_anomalies)

        self._total_anomalies_detected += len(anomalies)

        if anomalies:
            logger.info(
                f"Detected {len(anomalies)} anomaly/anomalies from {len(logs)} logs"
            )

        return anomalies

    def _run_rule_detection(self, logs: list[LogEntry]) -> list[AnomalyEvent]:
        """Run rule-based anomaly detection."""
        anomalies: list[AnomalyEvent] = []

        # Group logs by service for rule matching
        # Check each rule against all error/warn/fatal logs
        rule_matches: defaultdict[str, list[tuple[DetectionRule, LogEntry]]] = defaultdict(list)

        for log in logs:
            if log.log_level not in ("ERROR", "FATAL", "WARN"):
                continue

            for rule in RULES:
                if rule.matches(log.message):
                    service = log.pod_name.rsplit("-", 2)[0] if "-" in log.pod_name else log.pod_name
                    key = f"{rule.anomaly_type}:{service}"
                    rule_matches[key].append((rule, log))

        # Create anomaly events for rules that meet minimum match thresholds
        for key, matches in rule_matches.items():
            rule = matches[0][0]
            matched_logs = [m[1] for m in matches]
            service = key.split(":", 1)[1]

            if len(matches) < rule.min_matches:
                continue

            # Check cooldown
            if self._is_on_cooldown(key):
                continue

            # Record this anomaly for cooldown
            self._recent_anomalies[key] = datetime.utcnow()

            # Extract affected pods
            affected_pods = list({log.pod_name for log in matched_logs})

            anomaly = AnomalyEvent(
                anomaly_type=rule.anomaly_type,
                severity=self._severity_from_string(rule.severity),
                service_name=service,
                description=f"{rule.name}: {rule.description}",
                affected_pods=affected_pods,
                related_logs=matched_logs,
                confidence=min(0.5 + (len(matches) * 0.1), 0.95),
                detected_at=datetime.utcnow(),
                metrics={
                    "matched_patterns": len(matches),
                    "rule_name": rule.name,
                    "error_logs_count": len([l for l in matched_logs if l.log_level in ("ERROR", "FATAL")]),
                    "warning_logs_count": len([l for l in matched_logs if l.log_level == "WARN"]),
                },
            )
            anomalies.append(anomaly)
            logger.info(
                f"Rule-based anomaly: {rule.anomaly_type} on {service} "
                f"(confidence: {anomaly.confidence:.2f}, matches: {len(matches)})"
            )

        return anomalies

    def _run_statistical_detection(self, logs: list[LogEntry]) -> list[AnomalyEvent]:
        """Run statistical anomaly detection."""
        anomalies: list[AnomalyEvent] = []
        stat_anomalies = self.statistical_detector.check_all_services()

        for stat in stat_anomalies:
            service = stat["service"]
            key = f"statistical:{stat['metric']}:{service}"

            if self._is_on_cooldown(key):
                continue

            self._recent_anomalies[key] = datetime.utcnow()

            # Find related logs for this service
            related = [
                log for log in logs
                if service in log.pod_name and log.log_level in ("ERROR", "FATAL", "WARN")
            ]

            anomaly = AnomalyEvent(
                anomaly_type=f"Statistical_{stat['metric']}",
                severity=IncidentSeverity.MEDIUM,
                service_name=service,
                description=(
                    f"Statistical anomaly: {stat['metric']} for {service} "
                    f"(z-score: {stat['z_score']}, current: {stat.get('current_errors', stat.get('current_volume', 'N/A'))})"
                ),
                affected_pods=[],
                related_logs=related[-5:],  # last 5 relevant logs
                confidence=min(stat["z_score"] / 5.0, 0.9),
                detected_at=datetime.utcnow(),
                metrics=stat,
            )
            anomalies.append(anomaly)

        return anomalies

    def get_stats(self) -> dict:
        """Get detector statistics."""
        return {
            "total_logs_analyzed": self._total_logs_analyzed,
            "total_anomalies_detected": self._total_anomalies_detected,
            "active_cooldowns": len(self._recent_anomalies),
            "rules_loaded": len(RULES),
        }
