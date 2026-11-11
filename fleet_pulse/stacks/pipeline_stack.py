from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, telemetry_repo, dispatch_repo, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Artifact bucket with enforced encryption and SSL
        artifact_bucket = s3.Bucket(
            self, "PipelineArtifactBucket",
            bucket_name=f"fleetpulse-pipeline-artifacts-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Retrieve GitHub token secret created earlier in Secrets Manager
        github_token_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "ImportedGitHubToken", "github-token"
        )

        # CodeBuild project for building and pushing microservices
        build_role = iam.Role(
            self, "CodeBuildProjectRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )
        telemetry_repo.grant_pull_push(build_role)
        dispatch_repo.grant_pull_push(build_role)

        build_project = codebuild.PipelineProject(
            self, "FleetPulseBuildProject",
            project_name="fleetpulse-build",
            role=build_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml")
        )

        # CodePipeline definition
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")

        self.pipeline = codepipeline.Pipeline(
            self, "FleetPulsePipeline",
            pipeline_name="fleetpulse-ci-cd-pipeline",
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.GitHubSourceAction(
                            action_name="GitHub_Source",
                            owner="AbdullellahSWE",
                            repo="FleetPulse",
                            branch="main",
                            oauth_token=github_token_secret.secret_value,
                            output=source_output
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Docker_Build_Push",
                            project=build_project,
                            input=source_output,
                            outputs=[build_output]
                        )
                    ]
                )
            ]
        )

        # cdk-nag Security & Compliance Suppressions
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-S1", "reason": "Access logging optional for pipeline artifact bucket."},
            {"id": "AwsSolutions-IAM5", "reason": "CodeBuild ECR push permissions require wildcard image tags."},
            {"id": "AwsSolutions-CB4", "reason": "Service-managed encryption used for CodeBuild project logs/artifacts in PoC environment."},
        ])