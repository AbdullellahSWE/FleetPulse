"""Shared test configuration.

The API reads its Cognito settings when `auth` is first imported, so they must be set before ANY test
module imports the app. Doing it here (not in individual test files) makes results independent of
test-file ordering.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
os.environ.setdefault("AUTH_DEV_BYPASS", "false")
os.environ.pop("SNS_ALERT_TOPIC_ARN", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "telemetry-api"))
