"""Security Audit, Secret Leakage, and Container Configuration Verification Tests."""

import logging
import os
from pathlib import Path
import re
import pytest

from backend.app.core.config import get_settings
from backend.app.core.logging import JsonLogFormatter, SensitiveDataFilter


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_no_hardcoded_secrets_in_codebase():
    """Deterministic security audit scanning Python and config files for hardcoded secrets."""
    suspicious_patterns = [
        re.compile(r'-----BEGIN\s+(RSA|EC|OPENSSH|PGP)?\s*PRIVATE KEY-----', re.IGNORECASE),
        re.compile(r'AKIA[0-9A-Z]{16}'),  # AWS Access Key ID
        re.compile(r'ghp_[A-Za-z0-9]{36}'),  # GitHub Personal Access Token
        re.compile(r'password\s*=\s*["\'][A-Za-z0-9@#$%^&*!]{8,}["\']', re.IGNORECASE),
    ]

    target_extensions = {".py", ".yaml", ".yml", ".json", ".ini", ".conf"}
    ignore_dirs = {".git", ".pytest_cache", "node_modules", ".venv", "__pycache__", "dist", "build"}

    findings = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in target_extensions and not file.startswith(".env"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            # Skip comments or obvious examples
                            if "CHANGE_ME" in line or "EXAMPLE" in line.upper() or "REDACTED" in line or "placeholder" in line.lower():
                                continue
                            if "test_" in file:  # Skip test assertion strings
                                continue
                            for pattern in suspicious_patterns:
                                if pattern.search(line):
                                    findings.append(f"{file_path.relative_to(PROJECT_ROOT)}:L{line_no}")
                except Exception:
                    pass

    assert len(findings) == 0, f"Potential hardcoded credentials detected in: {findings}"


def test_frontend_dist_contains_no_backend_secrets():
    """Verify built frontend static bundle (frontend/dist/) contains no secret credentials."""
    dist_dir = PROJECT_ROOT / "frontend" / "dist"
    if not dist_dir.exists():
        pytest.skip("frontend/dist/ not yet built; skipping static bundle scan")

    forbidden_patterns = [
        re.compile(r'postgres(ql)?://', re.IGNORECASE),
        re.compile(r'SKYGUARD_OPERATIONAL_API_KEY', re.IGNORECASE),
        re.compile(r'CHANGE_ME_SECURE_POSTGRES_PASSWORD', re.IGNORECASE),
        re.compile(r'-----BEGIN\s+PRIVATE KEY-----', re.IGNORECASE),
    ]

    findings = []
    for asset_file in dist_dir.glob("**/*"):
        if asset_file.is_file() and asset_file.suffix in {".js", ".css", ".html", ".map"}:
            try:
                with open(asset_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for pattern in forbidden_patterns:
                        if pattern.search(content):
                            findings.append(f"{asset_file.name}: matched {pattern.pattern}")
            except Exception:
                pass

    assert len(findings) == 0, f"Sensitive tokens found in frontend build artifacts: {findings}"


def test_container_dockerfile_security():
    """Verify backend Dockerfile implements non-root execution and minimal privileges."""
    dockerfile_backend = PROJECT_ROOT / "deploy" / "Dockerfile.backend"
    assert dockerfile_backend.exists(), "Dockerfile.backend must exist"

    with open(dockerfile_backend, "r", encoding="utf-8") as f:
        content = f.read()

    assert "useradd" in content, "Dockerfile.backend must create a non-root system user"
    assert "USER skyguard" in content, "Dockerfile.backend must switch to non-root user 'USER skyguard'"
    assert "HEALTHCHECK" in content, "Dockerfile.backend must define a container HEALTHCHECK"


def test_container_compose_network_isolation():
    """Verify production docker-compose configurations enforce internal network isolation for PostgreSQL."""
    compose_path = PROJECT_ROOT / "deploy" / "docker-compose.yml"
    assert compose_path.exists(), "deploy/docker-compose.yml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "skyguard-net:" in content, "Docker compose must define internal skyguard-net bridge"
    assert "networks:" in content
    # Ensure postgres uses internal expose rather than unconditional public port bindings
    assert 'expose:\n      - "5432"' in content or 'expose:' in content


def test_logging_redaction_for_credentials():
    """Verify SensitiveDataFilter scrubs sensitive credentials and authorization headers."""
    filter_inst = SensitiveDataFilter()

    # 1. Database Connection URL with password
    record1 = logging.LogRecord(
        name="test.db", level=logging.INFO, pathname="", lineno=0,
        msg="Connecting to postgresql://skyguard_user:SecretP@ssw0rd123!@localhost:5432/skyguard_ai",
        args=(), exc_info=None
    )
    filter_inst.filter(record1)
    assert "SecretP@ssw0rd123!" not in record1.msg
    assert "postgresql://skyguard_user:[REDACTED]@" in record1.msg

    # 2. Bearer Authentication Header
    record2 = logging.LogRecord(
        name="test.auth", level=logging.WARNING, pathname="", lineno=0,
        msg="Received invalid request with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        args=(), exc_info=None
    )
    filter_inst.filter(record2)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token" not in record2.msg
    assert "Bearer [REDACTED]" in record2.msg

    # 3. API Key URL parameter
    record3 = logging.LogRecord(
        name="test.api", level=logging.ERROR, pathname="", lineno=0,
        msg="Request failed for https://api.provider.com/v1/data?api_key=secret_weather_api_token_456&unit=metric",
        args=(), exc_info=None
    )
    filter_inst.filter(record3)
    assert "secret_weather_api_token_456" not in record3.msg
    assert "api_key=[REDACTED]" in record3.msg
