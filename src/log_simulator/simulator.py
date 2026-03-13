"""Log Simulator - Generates realistic Kubernetes logs with injected anomalies."""

from __future__ import annotations

import asyncio
import logging
import random
import string
import uuid
from collections import deque
from datetime import datetime, timedelta

from src.models import LogEntry
from src.log_simulator.scenarios import (
    NORMAL_LOG_TEMPLATES,
    SERVICES,
    AnomalyScenario,
    get_random_scenario,
)

logger = logging.getLogger(__name__)


def _random_hash(length: int = 8) -> str:
    """Generate a random pod hash like 'a3f7b2c1'."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _fill_template(template: str) -> str:
    """Fill placeholders in a log template with realistic values."""
    replacements = {
        "{latency}": str(random.randint(5, 250)),
        "{order_id}": f"ORD-{random.randint(100000, 999999)}",
        "{user_id}": f"USR-{random.randint(1000, 9999)}",
        "{session_id}": str(uuid.uuid4())[:8],
        "{product_id}": f"PROD-{random.randint(100, 999)}",
        "{cart_id}": f"CART-{random.randint(1000, 9999)}",
        "{amount}": f"{random.uniform(9.99, 499.99):.2f}",
        "{quantity}": str(random.randint(1, 100)),
        "{ttl}": str(random.randint(60, 3600)),
        "{active}": str(random.randint(3, 12)),
        "{max}": "20",
        "{gc_time}": str(random.randint(10, 150)),
        "{heap}": str(random.randint(200, 600)),
        "{count}": str(random.randint(10, 500)),
        "{metric_count}": str(random.randint(50, 200)),
        "{pod_hash}": _random_hash(10),
        "{restart_count}": str(random.randint(1, 10)),
        "{txn_id}": str(uuid.uuid4())[:8],
        "{txn_id2}": str(uuid.uuid4())[:8],
    }
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


class LogSimulator:
    """Generates a continuous stream of realistic Kubernetes logs.

    Normal Mode: Generates routine operational logs.
    Anomaly Mode: Injects a realistic failure scenario with warning → error progression.
    """

    def __init__(
        self,
        anomaly_probability: float = 0.05,
        max_buffer_size: int = 5000,
    ):
        self.anomaly_probability = anomaly_probability
        self.log_buffer: deque[LogEntry] = deque(maxlen=max_buffer_size)
        self._running = False
        self._total_generated = 0
        self._anomalies_injected = 0
        self._current_anomaly: AnomalyScenario | None = None
        self._anomaly_phase: int = 0  # 0=normal_before, 1=warning, 2=error

    @property
    def total_generated(self) -> int:
        return self._total_generated

    @property
    def anomalies_injected(self) -> int:
        return self._anomalies_injected

    def generate_normal_log(self) -> LogEntry:
        """Generate a single normal operational log entry."""
        service = random.choice(SERVICES)
        template = random.choice(NORMAL_LOG_TEMPLATES)
        message = _fill_template(template)
        pod_suffix = _random_hash(10)

        entry = LogEntry(
            timestamp=datetime.utcnow(),
            namespace=service["namespace"],
            pod_name=f"{service['name']}-{pod_suffix}",
            container_name=service["container"],
            log_level="INFO",
            message=message,
            metadata={
                "node": f"worker-{random.randint(1, 5)}",
                "cluster": "demo-cluster",
            },
        )
        return entry

    def generate_anomaly_logs(self, scenario: AnomalyScenario) -> list[LogEntry]:
        """Generate a sequence of logs representing an anomaly scenario.

        This produces the full progression: normal → warning → error logs.
        """
        logs = []
        service_name = random.choice(scenario.services)
        service_info = next(
            (s for s in SERVICES if s["name"] == service_name),
            {"name": service_name, "namespace": "default", "container": service_name},
        )
        pod_suffix = _random_hash(10)
        base_time = datetime.utcnow()

        # Phase 1: Normal logs before the incident
        for i, template in enumerate(scenario.normal_logs_before):
            logs.append(LogEntry(
                timestamp=base_time + timedelta(seconds=i * 2),
                namespace=service_info["namespace"],
                pod_name=f"{service_info['name']}-{pod_suffix}",
                container_name=service_info.get("container", service_name),
                log_level="INFO",
                message=_fill_template(template),
                metadata={
                    "node": f"worker-{random.randint(1, 5)}",
                    "cluster": "demo-cluster",
                    "scenario": scenario.anomaly_type,
                    "phase": "pre-incident",
                },
            ))

        # Phase 2: Warning signals
        offset = len(scenario.normal_logs_before) * 2
        for i, template in enumerate(scenario.warning_logs):
            logs.append(LogEntry(
                timestamp=base_time + timedelta(seconds=offset + i * 5),
                namespace=service_info["namespace"],
                pod_name=f"{service_info['name']}-{pod_suffix}",
                container_name=service_info.get("container", service_name),
                log_level="WARN",
                message=_fill_template(template),
                metadata={
                    "node": f"worker-{random.randint(1, 5)}",
                    "cluster": "demo-cluster",
                    "scenario": scenario.anomaly_type,
                    "phase": "degradation",
                },
            ))

        # Phase 3: Error / fatal logs
        offset += len(scenario.warning_logs) * 5
        for i, template in enumerate(scenario.error_logs):
            level = "FATAL" if "FATAL" in template or "CRITICAL" in template else "ERROR"
            logs.append(LogEntry(
                timestamp=base_time + timedelta(seconds=offset + i * 3),
                namespace=service_info["namespace"],
                pod_name=f"{service_info['name']}-{pod_suffix}",
                container_name=service_info.get("container", service_name),
                log_level=level,
                message=_fill_template(template),
                metadata={
                    "node": f"worker-{random.randint(1, 5)}",
                    "cluster": "demo-cluster",
                    "scenario": scenario.anomaly_type,
                    "phase": "incident",
                },
            ))

        return logs

    def generate_batch(self, batch_size: int = 10) -> list[LogEntry]:
        """Generate a batch of logs, possibly including an anomaly.

        Returns:
            List of LogEntry objects. If an anomaly occurs, the batch will
            contain the full scenario log sequence.
        """
        logs: list[LogEntry] = []

        # Check if we should inject an anomaly
        if random.random() < self.anomaly_probability:
            scenario = get_random_scenario()
            anomaly_logs = self.generate_anomaly_logs(scenario)
            logs.extend(anomaly_logs)
            self._anomalies_injected += 1
            logger.info(
                f"Injected anomaly scenario: {scenario.name} "
                f"(type: {scenario.anomaly_type}, severity: {scenario.severity})"
            )
        else:
            # Generate normal operational logs
            for _ in range(batch_size):
                logs.append(self.generate_normal_log())

        # Add to buffer and update count
        for log in logs:
            self.log_buffer.append(log)
        self._total_generated += len(logs)

        return logs

    def get_recent_logs(self, count: int = 100) -> list[LogEntry]:
        """Get the most recent N logs from the buffer."""
        return list(self.log_buffer)[-count:]

    def get_all_logs(self) -> list[LogEntry]:
        """Get all logs currently in the buffer."""
        return list(self.log_buffer)

    def clear_buffer(self) -> int:
        """Clear the log buffer and return number of cleared logs."""
        count = len(self.log_buffer)
        self.log_buffer.clear()
        return count

    async def run_continuous(
        self, interval: float = 2.0, batch_size: int = 10
    ):
        """Run the simulator continuously, generating logs at the given interval.

        Args:
            interval: Seconds between each batch generation.
            batch_size: Number of normal logs per batch.
        """
        self._running = True
        logger.info(
            f"Log simulator started (interval={interval}s, batch_size={batch_size}, "
            f"anomaly_probability={self.anomaly_probability})"
        )

        while self._running:
            try:
                self.generate_batch(batch_size)
            except Exception as e:
                logger.error(f"Error generating log batch: {e}")
            await asyncio.sleep(interval)

        logger.info("Log simulator stopped.")

    def stop(self):
        """Stop the continuous simulator."""
        self._running = False
