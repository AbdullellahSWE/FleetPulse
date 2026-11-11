from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ecr as ecr,
)
from constructs import Construct

class EcrStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.telemetry_api_repo = ecr.Repository(
            self, "TelemetryApiRepo",
            repository_name="fleetpulse/telemetry-api",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        self.dispatch_service_repo = ecr.Repository(
            self, "DispatchServiceRepo",
            repository_name="fleetpulse/dispatch-service",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY
        )