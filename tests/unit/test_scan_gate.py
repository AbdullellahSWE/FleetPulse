"""Tests for the CI ECR scan gate (scripts/ci/ecr_scan_gate.py)."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

GATE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "ecr_scan_gate.py"
spec = importlib.util.spec_from_file_location("ecr_scan_gate", GATE_PATH)
gate = importlib.util.module_from_spec(spec)
sys.modules["ecr_scan_gate"] = gate
spec.loader.exec_module(gate)


def finding(name, severity):
    return {"name": name, "severity": severity, "uri": f"https://nvd.example/{name}"}


def test_counts_by_severity():
    counts, ignored = gate.count_findings(
        [finding("CVE-1", "CRITICAL"), finding("CVE-2", "HIGH"), finding("CVE-3", "HIGH"), finding("CVE-4", "LOW")], set()
    )
    assert counts["CRITICAL"] == 1 and counts["HIGH"] == 2 and counts["LOW"] == 1 and ignored == []


def test_allowlisted_cves_are_ignored():
    counts, ignored = gate.count_findings([finding("CVE-1", "CRITICAL"), finding("CVE-2", "CRITICAL")], {"CVE-1"})
    assert counts["CRITICAL"] == 1 and ignored == ["CVE-1"]


def test_unknown_severity_is_counted_not_dropped():
    counts, _ = gate.count_findings([finding("CVE-9", "SOMETHING_NEW")], set())
    assert counts["UNDEFINED"] == 1


def test_evaluate_blocks_critical_by_default():
    assert gate.evaluate({"CRITICAL": 1, "HIGH": 50}, max_critical=0, max_high=-1)
    assert gate.evaluate({"CRITICAL": 0, "HIGH": 50}, max_critical=0, max_high=-1) == []


def test_evaluate_high_threshold_only_when_enabled():
    assert gate.evaluate({"CRITICAL": 0, "HIGH": 3}, max_critical=0, max_high=2)
    assert gate.evaluate({"CRITICAL": 0, "HIGH": 2}, max_critical=0, max_high=2) == []


def test_allowlist_file_parsing(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("# header\nCVE-2024-1   # reason, expires 2027-01-01\n\nCVE-2024-2\n", encoding="utf-8")
    assert gate.load_allowlist(str(f)) == {"CVE-2024-1", "CVE-2024-2"}
    assert gate.load_allowlist(str(tmp_path / "missing.txt")) == set()


def _aws_responder(status, findings):
    def fake(args, region):
        if args[:2] == ["ecr", "start-image-scan"]:
            return {}
        return {"imageScanStatus": {"status": status, "description": "d"}, "imageScanFindings": {"findings": findings}}
    return fake


def test_run_passes_with_clean_scan(monkeypatch, capsys):
    monkeypatch.setattr(gate, "_aws", _aws_responder("COMPLETE", [finding("CVE-1", "MEDIUM")]))
    assert gate.run("repo", "abc", "us-east-1") == 0
    assert "GATE PASS" in capsys.readouterr().out


def test_run_fails_on_critical(monkeypatch, capsys):
    monkeypatch.setattr(gate, "_aws", _aws_responder("COMPLETE", [finding("CVE-1", "CRITICAL")]))
    assert gate.run("repo", "abc", "us-east-1") == 1
    assert "GATE FAIL" in capsys.readouterr().out


def test_run_fails_closed_when_scan_failed(monkeypatch, capsys):
    monkeypatch.setattr(gate, "_aws", _aws_responder("FAILED", []))
    assert gate.run("repo", "abc", "us-east-1") == 2


def test_run_fails_closed_on_unsupported_manifest(monkeypatch, capsys):
    def fake(args, region):
        raise RuntimeError("An error occurred (UnsupportedImageTypeException) when calling the StartImageScan operation")
    monkeypatch.setattr(gate, "_aws", fake)
    assert gate.run("repo", "abc", "us-east-1") == 2
    assert "DOCKER_BUILDKIT=0" in capsys.readouterr().out


def test_run_fails_closed_on_timeout(monkeypatch):
    monkeypatch.setenv("SCAN_TIMEOUT_SECONDS", "0")
    monkeypatch.setattr(gate, "_aws", _aws_responder("IN_PROGRESS", []))
    assert gate.run("repo", "abc", "us-east-1") == 2
