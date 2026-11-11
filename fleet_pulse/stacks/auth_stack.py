from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_cognito as cognito,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self, "FleetPulseUserPool",
            user_pool_name="fleetpulse-user-pool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        cognito.CfnUserPoolGroup(
            self, "DispatchManagerGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="DispatchManagers",
            description="Regional dispatch managers with depot access"
        )

        self.user_pool_client = cognito.UserPoolClient(
            self, "FleetPulseWebClient",
            user_pool=self.user_pool,
            user_pool_client_name="fleetpulse-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )

        # Place NagSuppressions inside __init__
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-COG8", "reason": "Cognito Advanced Security mode optional for PoC environment."},
            {"id": "AwsSolutions-COG2", "reason": "MFA configuration optional for PoC environment user pool."},
        ])