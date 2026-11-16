from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_iam as iam,
)
from aws_cdk.lambda_layer_kubectl_v31 import KubectlV31Layer
from cdk_nag import NagSuppressions
from constructs import Construct

class EksStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster_admin = iam.Role(
            self, "FleetPulseEksAdminRole",
            assumed_by=iam.AccountRootPrincipal()
        )

        kubectl_layer = KubectlV31Layer(self, "KubectlV31Layer")

        self.cluster = eks.Cluster(
            self, "FleetPulseEksCluster",
            cluster_name="fleetpulse-eks-cluster",
            version=eks.KubernetesVersion.V1_31,
            vpc=vpc,
            vpc_subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
            endpoint_access=eks.EndpointAccess.PRIVATE,
            cluster_logging=[
                eks.ClusterLoggingTypes.API,
                eks.ClusterLoggingTypes.AUDIT,
                eks.ClusterLoggingTypes.AUTHENTICATOR,
                eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
                eks.ClusterLoggingTypes.SCHEDULER,
            ],
            default_capacity=2,
            default_capacity_instance=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM
            ),
            masters_role=cluster_admin,
            kubectl_layer=kubectl_layer,
        )

        # IRSA: the telemetry API pods can assume a scoped IAM role (SNS publish only) instead of broad node-role permissions.
        self.api_service_account = self.cluster.add_service_account(
            "TelemetryApiServiceAccount", name="telemetry-api", namespace="default"
        )
        # (AI answers come from OpenRouter, so no Bedrock permissions are granted.)
        self.api_service_account.add_to_principal_policy(
            iam.PolicyStatement(
                sid="PublishVehicleAlerts",
                actions=["sns:Publish"],
                resources=[f"arn:aws:sns:{self.region}:{self.account}:fleetpulse-vehicle-alerts"],
            )
        )

        # CI/CD deploy access: the pipeline's CodeBuild role (fixed name, created in PipelineStack) may run kubectl.
        # Referenced by ARN string so there is no CloudFormation dependency cycle between the two stacks.
        deploy_role = iam.Role.from_role_arn(
            self, "PipelineDeployRole", f"arn:aws:iam::{self.account}:role/fleetpulse-codebuild-role", mutable=False
        )
        self.cluster.aws_auth.add_role_mapping(deploy_role, username="codebuild-deployer", groups=["system:masters"])

        # Allow in-VPC CodeBuild (deploy stage) to reach the Kubernetes API server.
        self.cluster.cluster_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(443), "Allow VPC workloads (CodeBuild deploy) to reach the EKS API"
        )

        # Suppress cdk-nag findings across EKS cluster constructs and internal provider nested stacks
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {"id": "AwsSolutions-IAM4", "reason": "AWS Managed Policies used by EKS cluster roles and CDK internal provider Lambdas."},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions required by EKS cluster creation policy and CDK internal provider framework."},
                {"id": "AwsSolutions-L1", "reason": "Lambda runtime version managed internally by AWS CDK EKS provider framework."},
                {"id": "AwsSolutions-SF1", "reason": "CloudWatch logging managed internally by AWS CDK EKS provider waiter state machine."},
                {"id": "AwsSolutions-SF2", "reason": "X-Ray tracing managed internally by AWS CDK EKS provider waiter state machine."},
                {"id": "AwsSolutions-EKS1", "reason": "EKS API server endpoint private access is enabled."},
                {"id": "AwsSolutions-EKS2", "reason": "EKS control plane logging is enabled."},
            ],
            apply_to_nested_stacks=True
        )