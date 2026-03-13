"""Rule-based anomaly detection patterns for Kubernetes logs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DetectionRule:
    """A rule that matches log patterns to detect specific anomalies."""

    name: str
    anomaly_type: str
    severity: str
    patterns: list[re.Pattern]
    min_matches: int = 1  # Minimum pattern matches to trigger
    description: str = ""

    def matches(self, message: str) -> bool:
        """Check if a log message matches any of the rule patterns."""
        return any(pattern.search(message) for pattern in self.patterns)


# ─────────────────────────────────────────────
# Detection Rules
# ─────────────────────────────────────────────

RULES: list[DetectionRule] = [
    DetectionRule(
        name="OOM Killed Detection",
        anomaly_type="OOMKilled",
        severity="critical",
        patterns=[
            re.compile(r"OOMKilled", re.IGNORECASE),
            re.compile(r"out\s*of\s*memory", re.IGNORECASE),
            re.compile(r"OutOfMemoryError", re.IGNORECASE),
            re.compile(r"exited with code 137", re.IGNORECASE),
            re.compile(r"exceeded memory limit", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects container OOM kills due to memory exhaustion",
    ),
    DetectionRule(
        name="CrashLoopBackOff Detection",
        anomaly_type="CrashLoopBackOff",
        severity="critical",
        patterns=[
            re.compile(r"CrashLoopBackOff", re.IGNORECASE),
            re.compile(r"Back-off restarting failed container", re.IGNORECASE),
            re.compile(r"Startup probe failed", re.IGNORECASE),
            re.compile(r"Cannot start service", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects containers in crash loop back-off state",
    ),
    DetectionRule(
        name="High Error Rate Detection",
        anomaly_type="HighErrorRate",
        severity="high",
        patterns=[
            re.compile(r"5\d{2}\s+(Internal Server Error|Bad Gateway|Service Unavailable)", re.IGNORECASE),
            re.compile(r"Circuit breaker OPEN", re.IGNORECASE),
            re.compile(r"consecutive failures", re.IGNORECASE),
            re.compile(r"NullPointerException|TypeError|AttributeError", re.IGNORECASE),
        ],
        min_matches=2,  # need at least 2 error matches
        description="Detects spikes in HTTP 5xx errors",
    ),
    DetectionRule(
        name="Database Connection Exhaustion",
        anomaly_type="DatabaseConnectionExhaustion",
        severity="high",
        patterns=[
            re.compile(r"Cannot acquire connection from pool", re.IGNORECASE),
            re.compile(r"QueuePool limit.*reached", re.IGNORECASE),
            re.compile(r"connection timed out|no database connection", re.IGNORECASE),
            re.compile(r"Deadlock detected", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects database connection pool exhaustion",
    ),
    DetectionRule(
        name="Disk Pressure Detection",
        anomaly_type="DiskPressure",
        severity="high",
        patterns=[
            re.compile(r"no space left on device", re.IGNORECASE),
            re.compile(r"DiskPressure", re.IGNORECASE),
            re.compile(r"disk full|ENOSPC", re.IGNORECASE),
            re.compile(r"flood stage disk watermark.*exceeded", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects disk pressure and volume capacity issues",
    ),
    DetectionRule(
        name="DNS/Network Failure Detection",
        anomaly_type="NetworkDNSFailure",
        severity="medium",
        patterns=[
            re.compile(r"DNS resolution failed|NXDOMAIN", re.IGNORECASE),
            re.compile(r"Name or service not known", re.IGNORECASE),
            re.compile(r"Failed to establish a new connection", re.IGNORECASE),
            re.compile(r"upstream_reset_before_response_started", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects DNS resolution and network connectivity failures",
    ),
    DetectionRule(
        name="CPU Throttling Detection",
        anomaly_type="CPUThrottling",
        severity="medium",
        patterns=[
            re.compile(r"CPU throttl", re.IGNORECASE),
            re.compile(r"periods? throttled", re.IGNORECASE),
            re.compile(r"deadline exceeded.*CPU", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects CPU throttling causing performance degradation",
    ),
    DetectionRule(
        name="Certificate Expiry Detection",
        anomaly_type="CertificateExpiry",
        severity="critical",
        patterns=[
            re.compile(r"certificate has expired", re.IGNORECASE),
            re.compile(r"ERR_CERT_DATE_INVALID", re.IGNORECASE),
            re.compile(r"TLS handshake failed.*expired", re.IGNORECASE),
            re.compile(r"client certificate expired", re.IGNORECASE),
        ],
        min_matches=1,
        description="Detects TLS/SSL certificate expiration issues",
    ),
]


def get_rule_by_type(anomaly_type: str) -> DetectionRule | None:
    """Find a detection rule by anomaly type."""
    for rule in RULES:
        if rule.anomaly_type == anomaly_type:
            return rule
    return None
