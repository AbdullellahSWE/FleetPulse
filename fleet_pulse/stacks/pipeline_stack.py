from aws_cdk import (
    Stack,
    SecretValue,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_kms as kms,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class PipelineStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, 
        telemetry_repo: ecr.IRepository, 
        dispatch_repo: ecr.IRepository, 
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        source_output = codepipeline.Artifact("SourceOutput")
        cb_key = kms.Key(self, "CodeBuildKey", enable_key_rotation=True)

        build_project = codebuild.PipelineProject(
            self, "FleetPulseBuildProject",
            project_name="fleetpulse-ci-build",
            encryption_key=cb_key,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "TELEMETRY_ECR_URI": codebuild.BuildEnvironmentVariable(value=telemetry_repo.repository_uri),
                "DISPATCH_ECR_URI": codebuild.BuildEnvironmentVariable(value=dispatch_repo.repository_uri),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml")
        )

        telemetry_repo.grant_pull_push(build_project)
        dispatch_repo.grant_pull_push(build_project)
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=["inspector2:StartCodeSecurityScan", "inspector2:GetCodeSecurityScanResults"],
                resources=["*"]
            )
        )

        codepipeline.Pipeline(
            self, "FleetPulsePipeline",
            pipeline_name="fleetpulse-cicd-pipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        cpactions.GitHubSourceAction(
                            action_name="GitHub_Source",
                            owner="AbdullellahSWE",
                            repo="FleetPulse",
                            branch="main",
                            oauth_token=SecretValue.secrets_manager("github-token"),
                            output=source_output
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="Build_Scan_Push",
                    actions=[
                        cpactions.CodeBuildAction(
                            action_name="Build_Container_Images",
                            project=build_project,
                            input=source_output
                        )
                    ]
                )
            ]
        )

        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-S1", "reason": "Access logging optional for transient pipeline artifact bucket."},
            {"id": "AwsSolutions-IAM5", "reason": "CodeBuild and CodePipeline default execution roles require wildcard scoping for build logs and ECR pushing."},
        ])