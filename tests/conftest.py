"""Shared test fixtures and configuration."""

import os
import sys
from pathlib import Path

import pytest

# Ensure the project root is on the path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Override settings for testing
os.environ["LLM_MOCK_MODE"] = "true"
os.environ["GITHUB_DRY_RUN"] = "true"
os.environ["SIMULATOR_ENABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./data/test_incidents.db"
os.environ["LOG_LEVEL"] = "DEBUG"
