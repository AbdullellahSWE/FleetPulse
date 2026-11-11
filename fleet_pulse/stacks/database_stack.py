from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.db_security_group = ec2.SecurityGroup(
            self, "AuroraSecurityGroup",
            vpc=vpc,
            description="Security group for FleetPulse Aurora PostgreSQL cluster",
            allow_all_outbound=True
        )

        self.db_cluster = rds.DatabaseCluster(
            self, "FleetPulseAuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            credentials=rds.Credentials.from_generated_secret("postgres"),
            storage_encrypted=True,
            iam_authentication=True,
            writer=rds.ClusterInstance.provisioned("WriterInstance", instance_type=ec2.InstanceType.of(ec2.InstanceClass.R6G, ec2.InstanceSize.LARGE)),
            readers=[
                rds.ClusterInstance.provisioned("ReaderInstance", instance_type=ec2.InstanceType.of(ec2.InstanceClass.R6G, ec2.InstanceSize.LARGE))
            ],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.db_security_group],
            removal_policy=RemovalPolicy.DESTROY
        )

        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-SMG4", "reason": "Automatic secret rotation disabled for PoC database credentials."},
            {"id": "AwsSolutions-RDS10", "reason": "Deletion protection disabled for PoC development lifecycle."},
        ])