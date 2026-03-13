"""Tests for the LLM Analyzer."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_analyzer.analyzer import LLMAnalyzer
from src.llm_analyzer.prompts import MOCK_RCA_TEMPLATES, SYSTEM_PROMPT
from src.models import AnomalyEvent, IncidentSeverity, LogEntry, RCAReport


def _make_anomaly(
    anomaly_type: str = "OOMKilled",
    service: str = "payment-service",
    severity: IncidentSeverity = IncidentSeverity.CRITICAL,
) -> AnomalyEvent:
    """Helper to create an anomaly event for testing."""
    return AnomalyEvent(
        anomaly_type=anomaly_type,
        severity=severity,
        service_name=service,
        description=f"Test anomaly: {anomaly_type}",
        affected_pods=[f"{service}-abc123"],
        related_logs=[
            LogEntry(
                timestamp=datetime.utcnow(),
                namespace="default",
                pod_name=f"{service}-abc123",
                container_name=service,
                log_level="ERROR",
                message=f"Test error for {anomaly_type}",
            )
        ],
        confidence=0.85,
        detected_at=datetime.utcnow(),
        metrics={"test": True},
    )


class TestLLMAnalyzer:
    """Tests for the LLMAnalyzer in mock mode."""

    @pytest.mark.asyncio
    async def test_mock_analysis_oom(self):
        """Test mock RCA for OOMKilled anomaly."""
        analyzer = LLMAnalyzer(mock_mode=True)
        anomaly = _make_anomaly("OOMKilled", "payment-service")
        rca = await analyzer.analyze(anomaly)

        assert isinstance(rca, RCAReport)
        assert "payment-service" in rca.incident_title
        assert "OOMKilled" in rca.incident_title or "Memory" in rca.incident_title
        assert rca.summary != ""
        assert rca.root_cause != ""
        assert len(rca.suggested_fixes) > 0
        assert len(rca.prevention_steps) > 0
        assert rca.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_mock_analysis_crashloop(self):
        """Test mock RCA for CrashLoopBackOff anomaly."""
        analyzer = LLMAnalyzer(mock_mode=True)
        anomaly = _make_anomaly("CrashLoopBackOff", "auth-service")
        rca = await analyzer.analyze(anomaly)

        assert isinstance(rca, RCAReport)
        assert "auth-service" in rca.incident_title
        assert rca.summary != ""
        assert len(rca.suggested_fixes) > 0

    @pytest.mark.asyncio
    async def test_mock_analysis_high_error_rate(self):
        """Test mock RCA for HighErrorRate anomaly."""
        analyzer = LLMAnalyzer(mock_mode=True)
        anomaly = _make_anomaly("HighErrorRate", "api-gateway", IncidentSeverity.HIGH)
        rca = await analyzer.analyze(anomaly)

        assert isinstance(rca, RCAReport)
        assert "api-gateway" in rca.summary or "api-gateway" in rca.incident_title

    @pytest.mark.asyncio
    async def test_mock_analysis_unknown_type(self):
        """Test mock RCA for unknown anomaly type uses default template."""
        analyzer = LLMAnalyzer(mock_mode=True)
        anomaly = _make_anomaly("UnknownAnomalyType", "test-service")
        rca = await analyzer.analyze(anomaly)

        assert isinstance(rca, RCAReport)
        assert rca.summary != ""
        assert len(rca.suggested_fixes) > 0

    @pytest.mark.asyncio
    async def test_all_known_types_have_templates(self):
        """Test that all known anomaly types produce valid RCA."""
        analyzer = LLMAnalyzer(mock_mode=True)

        for anomaly_type in MOCK_RCA_TEMPLATES:
            anomaly = _make_anomaly(anomaly_type, "test-service")
            rca = await analyzer.analyze(anomaly)
            assert isinstance(rca, RCAReport), f"Failed for {anomaly_type}"
            assert rca.incident_title != "", f"Empty title for {anomaly_type}"
            assert len(rca.suggested_fixes) > 0, f"No fixes for {anomaly_type}"


class TestPrompts:
    """Tests for prompt templates."""

    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        assert SYSTEM_PROMPT != ""
        assert "SRE" in SYSTEM_PROMPT or "Site Reliability" in SYSTEM_PROMPT

    def test_mock_templates_coverage(self):
        """Test that mock RCA templates cover major anomaly types."""
        expected_types = [
            "OOMKilled",
            "CrashLoopBackOff",
            "HighErrorRate",
            "DatabaseConnectionExhaustion",
            "DiskPressure",
            "NetworkDNSFailure",
            "CPUThrottling",
            "CertificateExpiry",
        ]
        for expected in expected_types:
            assert expected in MOCK_RCA_TEMPLATES, f"Missing template for {expected}"

    def test_mock_templates_have_required_fields(self):
        """Test that all mock RCA templates have required fields."""
        required_fields = ["title", "summary", "root_cause", "impact", "fixes", "prevention"]

        for name, template in MOCK_RCA_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Template {name} missing field: {field}"
