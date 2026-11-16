#!/usr/bin/env python3
"""ECR image-scan gate for CI.

Starts (or reuses) an ECR basic scan for repo:tag, waits for completion and exits non-zero when findings
exceed the configured thresholds. Fails CLOSED: a scan that cannot run or times out blocks the release.

Environment / flags (all optional):
  SCAN_MAX_CRITICAL   max allowed CRITICAL findings            (default 0)
  SCAN_MAX_HIGH       max allowed HIGH findings, -1 = ignore   (default -1)
  SCAN_ALLOWLIST      path to a file of CVE ids to ignore, one per line, '#' comments (default scan-allowlist.txt next to this script)
  SCAN_TIMEOUT_SECONDS  wait budget                            (default 600)

Usage: ecr_scan_gate.py <repository-name> <image-tag> [region]
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL", "UNDEFINED")


def load_allowlist(path: str) -> Set[str]:
    p = Path(path)
    if not p.is_file():
        return set()
    out = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def count_findings(findings: Iterable[dict], allowlist: Set[str]) -> Tuple[Dict[str, int], List[str]]:
    """Count findings per severity, ignoring allow-listed CVE ids. Returns (counts, ignored_ids)."""
    counts = {s: 0 for s in SEVERITIES}
    ignored: List[str] = []
    for f in findings:
        if f.get("name") in allowlist:
            ignored.append(f["name"])
            continue
        sev = f.get("severity", "UNDEFINED")
        counts[sev if sev in counts else "UNDEFINED"] += 1
    return counts, ignored


def evaluate(counts: Dict[str, int], max_critical: int, max_high: int) -> List[str]:
    """Return a list of human-readable violations (empty list == pass)."""
    problems = []
    if counts.get("CRITICAL", 0) > max_critical:
        problems.append(f"{counts['CRITICAL']} CRITICAL findings (max allowed {max_critical})")
    if max_high >= 0 and counts.get("HIGH", 0) > max_high:
        problems.append(f"{counts['HIGH']} HIGH findings (max allowed {max_high})")
    return problems


def _aws(args: List[str], region: str) -> dict:
    proc = subprocess.run(
        ["aws", *args, "--region", region, "--output", "json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",  # CVE descriptions contain non-ASCII characters
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},  # the AWS CLI also needs UTF-8 on Windows consoles
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def run(repo: str, tag: str, region: str) -> int:
    max_critical = int(os.getenv("SCAN_MAX_CRITICAL", "0"))
    max_high = int(os.getenv("SCAN_MAX_HIGH", "-1"))
    timeout = int(os.getenv("SCAN_TIMEOUT_SECONDS", "600"))
    allow_path = os.getenv("SCAN_ALLOWLIST", str(Path(__file__).with_name("scan-allowlist.txt")))
    allowlist = load_allowlist(allow_path)
    # Accept either a tag or an image digest ("sha256:...")
    image = ["--repository-name", repo, "--image-id", f"imageDigest={tag}" if tag.startswith("sha256:") else f"imageTag={tag}"]

    # scan-on-push may already have started one; StartImageScan then raises LimitExceeded/ScanInProgress, which is fine
    try:
        _aws(["ecr", "start-image-scan", *image], region)
    except RuntimeError as exc:
        text = str(exc)
        if "UnsupportedImageTypeException" in text:
            print(f"GATE FAIL: {repo}:{tag} uses a manifest type ECR cannot scan (build with DOCKER_BUILDKIT=0). {text}")
            return 2
        if not any(k in text for k in ("LimitExceededException", "already", "ScanInProgress")):
            print(f"GATE WARN: start-image-scan: {text}")

    deadline = time.time() + timeout
    status = "UNKNOWN"
    desc: dict = {}
    while time.time() < deadline:
        try:
            desc = _aws(["ecr", "describe-image-scan-findings", *image, "--max-items", "1000"], region)
        except RuntimeError as exc:
            if "ScanNotFoundException" in str(exc):
                time.sleep(5)
                continue
            print(f"GATE FAIL: could not read scan results: {exc}")
            return 2
        status = desc.get("imageScanStatus", {}).get("status", "UNKNOWN")
        if status in ("COMPLETE", "FAILED", "UNSUPPORTED_IMAGE", "FINDINGS_UNAVAILABLE"):
            break
        time.sleep(5)

    if status != "COMPLETE":
        print(f"GATE FAIL: scan for {repo}:{tag} ended with status {status}: {desc.get('imageScanStatus', {}).get('description', '')}")
        return 2

    findings = desc.get("imageScanFindings", {}).get("findings", [])
    counts, ignored = count_findings(findings, allowlist)
    print(f"Scan results for {repo}:{tag}: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v) + (f" (ignored {len(ignored)} allow-listed)" if ignored else ""))
    for f in findings:
        if f.get("severity") in ("CRITICAL", "HIGH") and f.get("name") not in allowlist:
            print(f"  [{f['severity']}] {f.get('name')}: {f.get('uri', '')}")

    problems = evaluate(counts, max_critical, max_high)
    if problems:
        print("GATE FAIL: " + "; ".join(problems))
        return 1
    print("GATE PASS")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(64)
    sys.exit(run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else os.getenv("AWS_REGION", "us-east-1")))
