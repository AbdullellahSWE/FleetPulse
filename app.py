#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from fleet_pulse.stacks.network_stack import NetworkStack
from fleet_pulse.stacks.ecr_stack import EcrStack
from fleet_pulse.stacks.eks_stack import EksStack
from fleet_pulse.stacks.database_stack import DatabaseStack
from fleet_pulse.stacks.streaming_stack import StreamingStack
from fleet_pulse.stacks.pipeline_stack import PipelineStack
from fleet_pulse.stacks.auth_stack import AuthStack
from fleet_pulse.stacks.ai_agent_stack import AiAgentStack
from fleet_pulse.stacks.observability_stack import ObservabilityStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or cdk.Aws.ACCOUNT_ID,
    region=app.node.try_get_context("region") or cdk.Aws.REGION
)

network_stack = NetworkStack(app, "FleetPulseNetworkStack", env=env)
ecr_stack = EcrStack(app, "FleetPulseEcrStack", env=env)
eks_stack = EksStack(app, "FleetPulseEksStack", vpc=network_stack.vpc, env=env)

database_stack = DatabaseStack(
    app, "FleetPulseDatabaseStack",
    vpc=network_stack.vpc,
    env=env
)

streaming_stack = StreamingStack(
    app, "FleetPulseStreamingStack",
    env=env
)

auth_stack = AuthStack(
    app, "FleetPulseAuthStack",
    env=env
)

ai_agent_stack = AiAgentStack(
    app, "FleetPulseAiAgentStack",
    env=env
)

observability_stack = ObservabilityStack(
    app, "FleetPulseObservabilityStack",
    env=env
)

pipeline_stack = PipelineStack(
    app, "FleetPulsePipelineStack",
    telemetry_repo=ecr_stack.telemetry_api_repo,
    dispatch_repo=ecr_stack.dispatch_service_repo,
    env=env
)

# Apply cdk-nag security checks across all stacks
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()