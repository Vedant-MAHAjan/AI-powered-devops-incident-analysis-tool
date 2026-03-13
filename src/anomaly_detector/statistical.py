"""Statistical anomaly detection for log streams."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np

from src.models import LogEntry

logger = logging.getLogger(__name__)


class StatisticalDetector:
    """Detects anomalies using statistical methods on log metrics.

    Tracks:
    - Error rate per service (errors / total logs)
    - Log volume spikes
    - Log level distribution shifts
    """

    def __init__(self, window_size: int = 100, z_score_threshold: float = 2.5):
        self.window_size = window_size
        self.z_score_threshold = z_score_threshold

        # Track error counts per service over time windows
        self._error_counts: defaultdict[str, list[int]] = defaultdict(list)
        self._total_counts: defaultdict[str, list[int]] = defaultdict(list)
        self._log_level_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def update_metrics(self, logs: list[LogEntry]) -> None:
        """Update internal metrics based on a new batch of logs."""
        # Count errors and totals per service
        service_errors: defaultdict[str, int] = defaultdict(int)
        service_totals: defaultdict[str, int] = defaultdict(int)

        for log in logs:
            service = log.pod_name.rsplit("-", 1)[0] if "-" in log.pod_name else log.pod_name
            service_totals[service] += 1
            self._log_level_counts[service][log.log_level] += 1

            if log.log_level in ("ERROR", "FATAL"):
                service_errors[service] += 1

        # Update rolling windows
        for service in service_totals:
            self._error_counts[service].append(service_errors.get(service, 0))
            self._total_counts[service].append(service_totals[service])

            # Keep window bounded
            if len(self._error_counts[service]) > self.window_size:
                self._error_counts[service] = self._error_counts[service][-self.window_size:]
                self._total_counts[service] = self._total_counts[service][-self.window_size:]

    def detect_error_rate_anomaly(self, service: str) -> dict | None:
        """Detect if a service has an abnormally high error rate using Z-score.

        Returns:
            Dict with anomaly details if detected, None otherwise.
        """
        error_counts = self._error_counts.get(service, [])
        if len(error_counts) < 5:  # Need enough data
            return None

        values = np.array(error_counts, dtype=float)
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return None

        latest = values[-1]
        z_score = (latest - mean) / std

        if z_score > self.z_score_threshold and latest > 0:
            return {
                "service": service,
                "metric": "error_rate",
                "z_score": round(float(z_score), 2),
                "current_errors": int(latest),
                "mean_errors": round(float(mean), 2),
                "std_errors": round(float(std), 2),
                "threshold": self.z_score_threshold,
            }

        return None

    def detect_volume_spike(self, service: str) -> dict | None:
        """Detect unusual spikes in log volume for a service.

        Returns:
            Dict with anomaly details if detected, None otherwise.
        """
        total_counts = self._total_counts.get(service, [])
        if len(total_counts) < 5:
            return None

        values = np.array(total_counts, dtype=float)
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return None

        latest = values[-1]
        z_score = (latest - mean) / std

        if z_score > self.z_score_threshold:
            return {
                "service": service,
                "metric": "log_volume",
                "z_score": round(float(z_score), 2),
                "current_volume": int(latest),
                "mean_volume": round(float(mean), 2),
                "std_volume": round(float(std), 2),
                "threshold": self.z_score_threshold,
            }

        return None

    def check_all_services(self) -> list[dict]:
        """Run anomaly detection across all tracked services.

        Returns:
            List of detected anomalies.
        """
        anomalies = []

        all_services = set(self._error_counts.keys()) | set(self._total_counts.keys())

        for service in all_services:
            error_anomaly = self.detect_error_rate_anomaly(service)
            if error_anomaly:
                anomalies.append(error_anomaly)
                logger.info(f"Statistical anomaly detected: {error_anomaly}")

            volume_anomaly = self.detect_volume_spike(service)
            if volume_anomaly:
                anomalies.append(volume_anomaly)
                logger.info(f"Volume spike detected: {volume_anomaly}")

        return anomalies

    def get_service_stats(self, service: str) -> dict:
        """Get current statistics for a service."""
        error_counts = self._error_counts.get(service, [])
        total_counts = self._total_counts.get(service, [])
        level_counts = dict(self._log_level_counts.get(service, {}))

        return {
            "service": service,
            "windows_tracked": len(error_counts),
            "total_errors": sum(error_counts),
            "total_logs": sum(total_counts),
            "error_rate": sum(error_counts) / max(sum(total_counts), 1),
            "log_level_distribution": level_counts,
        }
