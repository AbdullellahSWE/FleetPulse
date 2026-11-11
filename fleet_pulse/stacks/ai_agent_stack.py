from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_bedrock as bedrock,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class AiAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.agent_role = iam.Role(
            self, "FleetPulseBedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role allowing Bedrock Agent to query EV telemetry data"
        )

        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )
        )

        self.bedrock_agent = bedrock.CfnAgent(
            self, "FleetPulseDispatchAgent",
            agent_name="fleetpulse-dispatch-assistant",
            agent_resource_role_arn=self.agent_role.role_arn,
            foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            instruction="You are FleetPulse AI, an intelligent dispatch command assistant. Analyze real-time vehicle battery status, GPS telemetry, and routing diagnostics to assist dispatch managers."
        )

        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-IAM5", "reason": "Bedrock foundation model invocation policy uses wildcard resource scoping."},
        ])