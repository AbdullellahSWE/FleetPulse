from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    Tags,
)
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "FleetPulseVPC",
            max_azs=3,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            nat_gateways=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=20,
                ),
            ]
        )

        # Enable VPC Flow Logs
        self.vpc.add_flow_log(
            "VpcFlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs()
        )

        for subnet in self.vpc.private_subnets:
            Tags.of(subnet).add("kubernetes.io/role/internal-elb", "1")
            Tags.of(subnet).add("karpenter.sh/discovery", "fleetpulse-eks-cluster")
        for subnet in self.vpc.public_subnets:
            Tags.of(subnet).add("kubernetes.io/role/elb", "1")