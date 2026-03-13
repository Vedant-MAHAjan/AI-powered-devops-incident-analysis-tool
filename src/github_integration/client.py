"""GitHub client for creating incident issues."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from src.config import get_settings
from src.models import AnomalyEvent, RCAReport
from src.github_integration.templates import INCIDENT_ISSUE_TEMPLATE

logger = logging.getLogger(__name__)


class GitHubClient:
    """Creates GitHub issues for detected incidents.

    Supports:
    - Real mode: Uses PyGithub to create actual issues.
    - Dry-run mode: Logs the issue that would be created (for demo).
    """

    def __init__(self, dry_run: bool | None = None):
        settings = get_settings()
        self.dry_run = dry_run if dry_run is not None else settings.github_dry_run
        self.repo_owner = settings.github_repo_owner
        self.repo_name = settings.github_repo_name
        self._github = None
        self._repo = None

        if not self.dry_run:
            self._init_github(settings.github_token)

    def _init_github(self, token: str):
        """Initialize the GitHub client."""
        try:
            from github import Github

            if not token or token == "your_github_token_here":
                logger.warning("GitHub token not configured, switching to dry-run mode")
                self.dry_run = True
                return

            self._github = Github(token)
            self._repo = self._github.get_repo(f"{self.repo_owner}/{self.repo_name}")
            logger.info(f"GitHub client initialized for {self.repo_owner}/{self.repo_name}")
        except ImportError:
            logger.warning("PyGithub not installed, switching to dry-run mode")
            self.dry_run = True
        except Exception as e:
            logger.warning(f"Failed to initialize GitHub client: {e}")
            self.dry_run = True

    def create_incident_issue(
        self,
        anomaly: AnomalyEvent,
        rca: RCAReport,
    ) -> dict:
        """Create a GitHub issue for an incident.

        Args:
            anomaly: The detected anomaly event.
            rca: The root cause analysis report.

        Returns:
            Dict with issue details (url, number, title, body).
        """
        # Format the issue body
        body = self._format_issue_body(anomaly, rca)
        title = f"🚨 [{anomaly.severity.value.upper()}] {rca.incident_title}"

        # Determine labels
        labels = self._get_labels(anomaly)

        if self.dry_run:
            return self._dry_run_create(title, body, labels, anomaly)
        else:
            return self._real_create(title, body, labels)

    def _format_issue_body(self, anomaly: AnomalyEvent, rca: RCAReport) -> str:
        """Format the GitHub issue body from the template."""
        # Format fixes as numbered list
        fixes = "\n".join(f"{i+1}. {fix}" for i, fix in enumerate(rca.suggested_fixes))

        # Format prevention steps
        prevention = "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(rca.prevention_steps)
        )

        # Format log snippets
        log_snippets = "No logs available"
        if anomaly.related_logs:
            lines = []
            for log in anomaly.related_logs[-10:]:  # Last 10 log entries
                lines.append(
                    f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"[{log.log_level:5s}] [{log.pod_name}] {log.message}"
                )
            log_snippets = "\n".join(lines)

        # Format metrics
        metrics = json.dumps(anomaly.metrics, indent=2, default=str)

        # Determine LLM mode
        settings = get_settings()
        llm_mode = "template-based (mock)" if settings.llm_mock_mode else f"Ollama ({settings.ollama_model})"

        return INCIDENT_ISSUE_TEMPLATE.format(
            detected_at=anomaly.detected_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            severity=anomaly.severity.value.upper(),
            service_name=anomaly.service_name,
            anomaly_type=anomaly.anomaly_type,
            confidence_score=rca.confidence_score,
            summary=rca.summary,
            root_cause=rca.root_cause,
            impact=rca.impact,
            fixes=fixes,
            prevention=prevention,
            log_snippets=log_snippets,
            metrics=metrics,
            llm_mode=llm_mode,
        )

    def _get_labels(self, anomaly: AnomalyEvent) -> list[str]:
        """Generate GitHub labels for the issue."""
        labels = ["incident", "auto-generated"]

        # Severity label
        labels.append(f"severity:{anomaly.severity.value}")

        # Type label
        type_labels = {
            "OOMKilled": "type:memory",
            "CrashLoopBackOff": "type:crash",
            "HighErrorRate": "type:errors",
            "DatabaseConnectionExhaustion": "type:database",
            "DiskPressure": "type:disk",
            "NetworkDNSFailure": "type:network",
            "CPUThrottling": "type:cpu",
            "CertificateExpiry": "type:security",
        }
        base_type = anomaly.anomaly_type.replace("Statistical_", "")
        if base_type in type_labels:
            labels.append(type_labels[base_type])

        return labels

    def _dry_run_create(
        self, title: str, body: str, labels: list[str], anomaly: AnomalyEvent
    ) -> dict:
        """Simulate issue creation in dry-run mode."""
        import random

        fake_number = random.randint(1, 9999)
        fake_url = (
            f"https://github.com/{self.repo_owner or 'demo-user'}"
            f"/{self.repo_name}/issues/{fake_number}"
        )

        logger.info(f"[DRY RUN] Would create GitHub issue: {title}")
        logger.info(f"[DRY RUN] Labels: {labels}")
        logger.info(f"[DRY RUN] Fake URL: {fake_url}")

        return {
            "url": fake_url,
            "number": fake_number,
            "title": title,
            "body": body,
            "labels": labels,
            "dry_run": True,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _real_create(self, title: str, body: str, labels: list[str]) -> dict:
        """Create an actual GitHub issue."""
        try:
            # Ensure labels exist (create if they don't)
            existing_labels = [label.name for label in self._repo.get_labels()]
            for label in labels:
                if label not in existing_labels:
                    try:
                        self._repo.create_label(name=label, color="d73a4a")
                    except Exception:
                        pass  # Label might already exist, ignore

            issue = self._repo.create_issue(
                title=title,
                body=body,
                labels=labels,
            )

            logger.info(f"Created GitHub issue #{issue.number}: {title}")

            return {
                "url": issue.html_url,
                "number": issue.number,
                "title": title,
                "body": body,
                "labels": labels,
                "dry_run": False,
                "created_at": issue.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return {
                "url": None,
                "number": None,
                "title": title,
                "body": body,
                "labels": labels,
                "dry_run": False,
                "error": str(e),
                "created_at": datetime.utcnow().isoformat(),
            }
