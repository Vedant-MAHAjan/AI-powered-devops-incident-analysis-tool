"""Tests for the Log Simulator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.log_simulator.simulator import LogSimulator
from src.log_simulator.scenarios import SCENARIOS, get_random_scenario, get_scenario_by_type
from src.models import LogEntry


class TestLogSimulator:
    """Tests for the LogSimulator class."""

    def test_generate_normal_log(self):
        """Test that a normal log entry is generated correctly."""
        simulator = LogSimulator()
        log = simulator.generate_normal_log()

        assert isinstance(log, LogEntry)
        assert log.log_level == "INFO"
        assert log.namespace == "default"
        assert log.pod_name != ""
        assert log.container_name != ""
        assert log.message != ""
        assert log.timestamp is not None

    def test_generate_batch_normal(self):
        """Test batch generation of normal logs."""
        simulator = LogSimulator(anomaly_probability=0.0)  # No anomalies
        logs = simulator.generate_batch(batch_size=10)

        assert len(logs) == 10
        assert all(isinstance(log, LogEntry) for log in logs)
        assert all(log.log_level == "INFO" for log in logs)
        assert simulator.total_generated == 10

    def test_generate_batch_with_anomaly(self):
        """Test batch generation with guaranteed anomaly."""
        simulator = LogSimulator(anomaly_probability=1.0)  # Always anomaly
        logs = simulator.generate_batch(batch_size=10)

        # Anomaly batches contain multiple log entries (normal + warn + error)
        assert len(logs) > 0
        assert simulator.anomalies_injected == 1

        # Should have mixed log levels
        levels = {log.log_level for log in logs}
        assert len(levels) > 1  # Should have more than just INFO

    def test_log_buffer(self):
        """Test that logs are buffered correctly."""
        simulator = LogSimulator(anomaly_probability=0.0)
        simulator.generate_batch(batch_size=5)
        simulator.generate_batch(batch_size=5)

        assert len(simulator.get_all_logs()) == 10
        assert len(simulator.get_recent_logs(count=3)) == 3
        assert simulator.total_generated == 10

    def test_clear_buffer(self):
        """Test clearing the log buffer."""
        simulator = LogSimulator(anomaly_probability=0.0)
        simulator.generate_batch(batch_size=10)
        cleared = simulator.clear_buffer()

        assert cleared == 10
        assert len(simulator.get_all_logs()) == 0

    def test_buffer_max_size(self):
        """Test that buffer respects max size."""
        simulator = LogSimulator(anomaly_probability=0.0, max_buffer_size=20)
        simulator.generate_batch(batch_size=15)
        simulator.generate_batch(batch_size=15)

        assert len(simulator.get_all_logs()) == 20  # Capped at max

    def test_anomaly_log_sequence(self):
        """Test that anomaly logs follow the correct progression."""
        simulator = LogSimulator()
        scenario = get_scenario_by_type("OOMKilled")
        assert scenario is not None

        logs = simulator.generate_anomaly_logs(scenario)
        assert len(logs) > 0

        # Check log level progression: INFO → WARN → ERROR/FATAL
        found_info = False
        found_warn = False
        found_error = False

        for log in logs:
            if log.log_level == "INFO":
                found_info = True
            elif log.log_level == "WARN":
                found_warn = True
            elif log.log_level in ("ERROR", "FATAL"):
                found_error = True

        assert found_info, "Should have INFO logs before the incident"
        assert found_warn, "Should have WARN logs during degradation"
        assert found_error, "Should have ERROR/FATAL logs during incident"


class TestScenarios:
    """Tests for anomaly scenarios."""

    def test_scenarios_exist(self):
        """Test that scenario definitions are loaded."""
        assert len(SCENARIOS) > 0

    def test_get_random_scenario(self):
        """Test random scenario selection."""
        scenario = get_random_scenario()
        assert scenario is not None
        assert scenario.name != ""
        assert scenario.anomaly_type != ""
        assert scenario.severity in ("critical", "high", "medium", "low")

    def test_get_scenario_by_type(self):
        """Test finding scenario by type."""
        scenario = get_scenario_by_type("OOMKilled")
        assert scenario is not None
        assert scenario.anomaly_type == "OOMKilled"
        assert scenario.severity == "critical"

    def test_get_scenario_by_type_not_found(self):
        """Test that missing scenario returns None."""
        scenario = get_scenario_by_type("NonExistentType")
        assert scenario is None

    def test_all_scenarios_have_required_fields(self):
        """Test that all scenarios have complete data."""
        for scenario in SCENARIOS:
            assert scenario.name, f"Scenario missing name"
            assert scenario.anomaly_type, f"Scenario {scenario.name} missing anomaly_type"
            assert scenario.severity in ("critical", "high", "medium", "low"), (
                f"Scenario {scenario.name} has invalid severity: {scenario.severity}"
            )
            assert len(scenario.services) > 0, f"Scenario {scenario.name} has no services"
            assert len(scenario.error_logs) > 0, f"Scenario {scenario.name} has no error logs"
            assert len(scenario.warning_logs) > 0, f"Scenario {scenario.name} has no warning logs"
