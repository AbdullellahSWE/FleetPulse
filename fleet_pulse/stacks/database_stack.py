from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Database Admin Credentials Secret
        self.db_secret = secretsmanager.Secret(
            self, "FleetPulseDbSecret",
            secret_name="fleetpulse-db-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_punctuation=True,
            )
        )

        # Database Security Group
        db_sg = ec2.SecurityGroup(
            self, "FleetPulseDbSecurityGroup",
            vpc=vpc,
            description="Security group for FleetPulse Aurora PostgreSQL Serverless v2 DB Cluster",
            allow_all_outbound=False
        )

        # Allow inbound PostgreSQL access from inside the VPC
        db_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from inside VPC"
        )

        # Aurora PostgreSQL Serverless v2 Cluster using default engine version
        self.db_cluster = rds.DatabaseCluster(
            self, "FleetPulseAuroraCluster",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            credentials=rds.Credentials.from_secret(self.db_secret),
            writer=rds.ClusterInstance.serverless_v2("WriterInstance"),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4.0,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_sg],
            storage_encrypted=True,
            default_database_name="fleetpulse",
            removal_policy=RemovalPolicy.DESTROY
        )

        # cdk-nag Security & Compliance Suppressions
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-RDS6", "reason": "IAM Database Authentication disabled for PoC deployment."},
            {"id": "AwsSolutions-RDS10", "reason": "Deletion protection disabled for PoC deployment testing."},
            {"id": "AwsSolutions-SMG4", "reason": "Automatic secret rotation optional for PoC deployment."},
        ])