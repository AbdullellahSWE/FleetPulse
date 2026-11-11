from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct

class ObservabilityStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Operational CloudWatch Dashboard for Telemetry Ingestion & Cluster Health
        self.dashboard = cloudwatch.Dashboard(
            self, "FleetPulseOperationalDashboard",
            dashboard_name="FleetPulse-Telemetry-Ops"
        )

        # Widget 1: Kinesis Telemetry Ingestion Rate
        kinesis_metric = cloudwatch.Metric(
            namespace="AWS/Kinesis",
            metric_name="IncomingRecords",
            dimensions_map={"StreamName": "fleetpulse-telemetry-stream"}
        )

        # Widget 2: Aurora Database Connections
        db_metric = cloudwatch.Metric(
            namespace="AWS/RDS",
            metric_name="DatabaseConnections"
        )

        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Kinesis Ingestion Stream Throughput",
                left=[kinesis_metric]
            ),
            cloudwatch.GraphWidget(
                title="Aurora DB Connections",
                left=[db_metric]
            )
        )