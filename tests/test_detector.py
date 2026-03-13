"""Tests for the Anomaly Detector."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.anomaly_detector.detector import AnomalyDetector
from src.anomaly_detector.rules import RULES, get_rule_by_type
from src.anomaly_detector.statistical import StatisticalDetector
from src.models import LogEntry


def _make_log(message: str, level: str = "ERROR", pod: str = "test-service-abc123") -> LogEntry:
    """Helper to create a log entry for testing."""
    return LogEntry(
        timestamp=datetime.utcnow(),
        namespace="default",
        pod_name=pod,
        container_name="test-container",
        log_level=level,
        message=message,
    )


class TestRules:
    """Tests for detection rules."""

    def test_rules_loaded(self):
        """Test that detection rules are loaded."""
        assert len(RULES) > 0

    def test_oom_rule_matches(self):
        """Test OOMKilled rule pattern matching."""
        rule = get_rule_by_type("OOMKilled")
        assert rule is not None
        assert rule.matches("Container killed due to OOMKilled")
        assert rule.matches("java.lang.OutOfMemoryError: Java heap space")
        assert rule.matches("Process exited with code 137 (OOMKilled)")
        assert not rule.matches("GET /api/v1/products - 200 OK")

    def test_crashloop_rule_matches(self):
        """Test CrashLoopBackOff rule matching."""
        rule = get_rule_by_type("CrashLoopBackOff")
        assert rule is not None
        assert rule.matches("Entering CrashLoopBackOff")
        assert rule.matches("Back-off restarting failed container")
        assert not rule.matches("Healthy pod running")

    def test_high_error_rate_matches(self):
        """Test high error rate rule matching."""
        rule = get_rule_by_type("HighErrorRate")
        assert rule is not None
        assert rule.matches("500 Internal Server Error")
        assert rule.matches("502 Bad Gateway")
        assert rule.matches("Circuit breaker OPEN for service")
        assert not rule.matches("200 OK")

    def test_disk_pressure_matches(self):
        """Test disk pressure rule matching."""
        rule = get_rule_by_type("DiskPressure")
        assert rule is not None
        assert rule.matches("Write failed: no space left on device")
        assert rule.matches("Node condition DiskPressure detected")

    def test_certificate_expiry_matches(self):
        """Test certificate expiry rule matching."""
        rule = get_rule_by_type("CertificateExpiry")
        assert rule is not None
        assert rule.matches("TLS handshake failed: x509: certificate has expired")
        assert rule.matches("ERR_CERT_DATE_INVALID")


class TestAnomalyDetector:
    """Tests for the AnomalyDetector class."""

    def test_no_anomalies_in_normal_logs(self):
        """Test that normal logs don't trigger anomalies."""
        detector = AnomalyDetector()
        logs = [
            _make_log("GET /api/v1/products - 200 OK (23ms)", level="INFO"),
            _make_log("Health check passed", level="INFO"),
            _make_log("Cache hit for session abc123", level="INFO"),
        ]
        anomalies = detector.analyze_logs(logs)
        assert len(anomalies) == 0
        assert detector.total_logs_analyzed == 3

    def test_detects_oom_killed(self):
        """Test detection of OOMKilled anomaly."""
        detector = AnomalyDetector()
        logs = [
            _make_log("Memory usage at 96% of limit", level="WARN"),
            _make_log("FATAL: Container killed due to OOMKilled", level="FATAL"),
            _make_log("java.lang.OutOfMemoryError: Java heap space"),
        ]
        anomalies = detector.analyze_logs(logs)
        assert len(anomalies) > 0
        assert any(a.anomaly_type == "OOMKilled" for a in anomalies)

    def test_detects_crashloop(self):
        """Test detection of CrashLoopBackOff."""
        detector = AnomalyDetector()
        logs = [
            _make_log("Back-off restarting failed container auth-service", level="ERROR"),
            _make_log("Startup probe failed: HTTP probe failed", level="ERROR"),
        ]
        anomalies = detector.analyze_logs(logs)
        assert len(anomalies) > 0
        assert any(a.anomaly_type == "CrashLoopBackOff" for a in anomalies)

    def test_anomaly_cooldown(self):
        """Test that the same anomaly type isn't reported repeatedly."""
        detector = AnomalyDetector()
        detector._cooldown_seconds = 300  # 5 min cooldown

        logs = [
            _make_log("Container killed due to OOMKilled", level="FATAL"),
        ]

        # First detection should succeed
        anomalies1 = detector.analyze_logs(logs)
        assert len(anomalies1) > 0

        # Second detection within cooldown should be suppressed
        anomalies2 = detector.analyze_logs(logs)
        oom_anomalies = [a for a in anomalies2 if a.anomaly_type == "OOMKilled"]
        assert len(oom_anomalies) == 0

    def test_detector_stats(self):
        """Test detector statistics."""
        detector = AnomalyDetector()
        logs = [
            _make_log("Normal log", level="INFO"),
            _make_log("Another normal log", level="INFO"),
        ]
        detector.analyze_logs(logs)

        stats = detector.get_stats()
        assert stats["total_logs_analyzed"] == 2
        assert stats["rules_loaded"] > 0


class TestStatisticalDetector:
    """Tests for statistical anomaly detection."""

    def test_no_anomaly_with_stable_data(self):
        """Test that stable error counts don't trigger anomalies."""
        detector = StatisticalDetector(z_score_threshold=2.5)

        for _ in range(20):
            logs = [_make_log("Normal log", level="INFO") for _ in range(5)]
            detector.update_metrics(logs)

        anomalies = detector.check_all_services()
        assert len(anomalies) == 0

    def test_detects_error_rate_spike(self):
        """Test detection of a sudden error rate spike."""
        detector = StatisticalDetector(z_score_threshold=2.0)

        # First, feed normal data for baseline
        for _ in range(20):
            normal_logs = [_make_log("Normal log", level="INFO") for _ in range(10)]
            detector.update_metrics(normal_logs)

        # Now inject a spike of errors
        error_logs = [_make_log("Server error 500", level="ERROR") for _ in range(15)]
        detector.update_metrics(error_logs)

        anomalies = detector.check_all_services()
        # Should detect the error rate spike
        assert len(anomalies) > 0

    def test_service_stats(self):
        """Test getting service statistics."""
        detector = StatisticalDetector()

        logs = [
            _make_log("Normal log", level="INFO"),
            _make_log("Warning log", level="WARN"),
            _make_log("Error log", level="ERROR"),
        ]
        detector.update_metrics(logs)

        stats = detector.get_service_stats("test-service")
        assert stats["service"] == "test-service"
        assert stats["total_logs"] > 0
