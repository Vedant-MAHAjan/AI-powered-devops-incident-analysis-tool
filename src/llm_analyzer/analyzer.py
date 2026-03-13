"""LLM Analyzer - Root Cause Analysis using Ollama (local LLM) or mock mode."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from src.config import get_settings
from src.models import AnomalyEvent, RCAReport
from src.llm_analyzer.prompts import (
    ANALYSIS_PROMPT,
    DEFAULT_MOCK_RCA,
    MOCK_RCA_TEMPLATES,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Analyzes anomalies and generates Root Cause Analysis reports.

    Supports two modes:
    1. Ollama mode: Uses a locally running Ollama instance with Llama/Mistral.
    2. Mock mode: Uses pre-built RCA templates (for demo without Ollama).
    """

    def __init__(self, mock_mode: bool | None = None):
        settings = get_settings()
        self.mock_mode = mock_mode if mock_mode is not None else settings.llm_mock_mode
        self.ollama_base_url = settings.ollama_base_url
        self.ollama_model = settings.ollama_model
        self._ollama_client = None

        if not self.mock_mode:
            self._init_ollama()

    def _init_ollama(self):
        """Initialize the Ollama client."""
        try:
            import ollama
            self._ollama_client = ollama.Client(host=self.ollama_base_url)
            # Test connection
            self._ollama_client.list()
            logger.info(f"Ollama client initialized (model: {self.ollama_model})")
        except ImportError:
            logger.warning("ollama package not installed, falling back to mock mode")
            self.mock_mode = True
        except Exception as e:
            logger.warning(f"Failed to connect to Ollama at {self.ollama_base_url}: {e}")
            logger.warning("Falling back to mock mode")
            self.mock_mode = True

    async def analyze(self, anomaly: AnomalyEvent) -> RCAReport:
        """Generate a Root Cause Analysis report for an anomaly.

        Args:
            anomaly: The detected anomaly event.

        Returns:
            RCAReport with structured root cause analysis.
        """
        logger.info(
            f"Analyzing anomaly: {anomaly.anomaly_type} on {anomaly.service_name} "
            f"(mode: {'mock' if self.mock_mode else 'ollama'})"
        )

        if self.mock_mode:
            return self._mock_analyze(anomaly)
        else:
            return await self._ollama_analyze(anomaly)

    async def _ollama_analyze(self, anomaly: AnomalyEvent) -> RCAReport:
        """Generate RCA using Ollama local LLM."""
        try:
            # Format log entries for the prompt
            log_entries = self._format_logs(anomaly)
            metrics_str = json.dumps(anomaly.metrics, indent=2, default=str)

            prompt = ANALYSIS_PROMPT.format(
                anomaly_type=anomaly.anomaly_type,
                service_name=anomaly.service_name,
                severity=anomaly.severity.value,
                detected_at=anomaly.detected_at.isoformat(),
                affected_pods=", ".join(anomaly.affected_pods) or "N/A",
                confidence=f"{anomaly.confidence:.2f}",
                metrics=metrics_str,
                log_entries=log_entries,
            )

            # Call Ollama
            response = self._ollama_client.chat(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": 0.3,  # Lower temperature for more focused analysis
                    "num_predict": 1500,
                },
            )

            raw_response = response["message"]["content"]
            return self._parse_llm_response(raw_response, anomaly)

        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}, falling back to mock")
            return self._mock_analyze(anomaly)

    def _mock_analyze(self, anomaly: AnomalyEvent) -> RCAReport:
        """Generate RCA using pre-built templates (mock mode)."""
        # Get the template for this anomaly type
        base_type = anomaly.anomaly_type.replace("Statistical_", "")
        template = MOCK_RCA_TEMPLATES.get(base_type, DEFAULT_MOCK_RCA)

        # Fill in service name
        service = anomaly.service_name
        title = template["title"].format(
            service=service, anomaly_type=anomaly.anomaly_type
        )
        summary = template["summary"].format(
            service=service, anomaly_type=anomaly.anomaly_type
        )
        root_cause = template["root_cause"].format(
            service=service, anomaly_type=anomaly.anomaly_type
        )
        impact = template["impact"].format(
            service=service, anomaly_type=anomaly.anomaly_type
        )
        fixes = [f.format(service=service) for f in template["fixes"]]
        prevention = [p.format(service=service) for p in template["prevention"]]

        return RCAReport(
            incident_title=title,
            summary=summary,
            root_cause=root_cause,
            impact=impact,
            suggested_fixes=fixes,
            prevention_steps=prevention,
            confidence_score=anomaly.confidence,
            raw_llm_response=f"[MOCK MODE] Template-based RCA for {anomaly.anomaly_type}",
        )

    def _parse_llm_response(self, raw_response: str, anomaly: AnomalyEvent) -> RCAReport:
        """Parse the structured LLM response into an RCAReport."""
        try:
            # Extract sections using regex
            title = self._extract_section(raw_response, "Incident Title") or (
                f"{anomaly.anomaly_type} - {anomaly.service_name}"
            )
            summary = self._extract_section(raw_response, "Summary") or "Analysis pending"
            root_cause = self._extract_section(raw_response, "Root Cause") or "See raw response"
            impact = self._extract_section(raw_response, "Impact") or "Impact assessment pending"

            fixes_text = self._extract_section(raw_response, "Suggested Fixes") or ""
            fixes = self._extract_list_items(fixes_text) or ["Review the incident logs manually"]

            prevention_text = self._extract_section(raw_response, "Prevention Steps") or ""
            prevention = self._extract_list_items(prevention_text) or [
                "Set up monitoring for this failure type"
            ]

            return RCAReport(
                incident_title=title.strip(),
                summary=summary.strip(),
                root_cause=root_cause.strip(),
                impact=impact.strip(),
                suggested_fixes=fixes,
                prevention_steps=prevention,
                confidence_score=anomaly.confidence,
                raw_llm_response=raw_response,
            )

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return RCAReport(
                incident_title=f"{anomaly.anomaly_type} - {anomaly.service_name}",
                summary=raw_response[:500],
                root_cause=raw_response,
                impact="See full analysis",
                suggested_fixes=["Review the full LLM output"],
                prevention_steps=["Set up monitoring"],
                confidence_score=anomaly.confidence,
                raw_llm_response=raw_response,
            )

    @staticmethod
    def _extract_section(text: str, section_name: str) -> str | None:
        """Extract a section from the LLM's markdown response."""
        pattern = rf"##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_list_items(text: str) -> list[str]:
        """Extract numbered or bulleted list items from text."""
        items = re.findall(r"(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+)", text)
        return [item.strip() for item in items if item.strip()]

    @staticmethod
    def _format_logs(anomaly: AnomalyEvent) -> str:
        """Format log entries for inclusion in the prompt."""
        if not anomaly.related_logs:
            return "No log entries available"

        lines = []
        for log in anomaly.related_logs:
            lines.append(
                f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"[{log.log_level:5s}] "
                f"[{log.pod_name}] "
                f"{log.message}"
            )
        return "\n".join(lines)
