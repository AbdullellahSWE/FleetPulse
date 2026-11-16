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

        # 1. Artifact bucket with enforced encryption and SSL
        artifact_bucket = s3.Bucket(
            self, "PipelineArtifactBucket",
            bucket_name=f"fleetpulse-pipeline-artifacts-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 2. Retrieve GitHub token secret dynamically from Secrets Manager
        github_token_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "ImportedGitHubToken", "github-token"
        )

        # 3. CodeBuild project for building microservices
        # Fixed role name: EksStack maps this exact ARN into aws-auth so the deploy stage can run kubectl.
        build_role = iam.Role(
            self, "CodeBuildProjectRole",
            role_name="fleetpulse-codebuild-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )
        telemetry_repo.grant_pull_push(build_role)
        dispatch_repo.grant_pull_push(build_role)

        # Repositories actually used by the deployed workloads + scan-gate permissions
        for repo_name in ("fleetpulse-telemetry-api", "fleetpulse-dispatch-service", "fleetpulse/dashboard"):
            repo_arn = f"arn:aws:ecr:{self.region}:{self.account}:repository/{repo_name}"
            build_role.add_to_policy(iam.PolicyStatement(
                actions=[
                    "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
                    "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
                    "ecr:StartImageScan", "ecr:DescribeImageScanFindings", "ecr:DescribeImages",
                ],
                resources=[repo_arn],
            ))
        build_role.add_to_policy(iam.PolicyStatement(actions=["ecr:GetAuthorizationToken", "sts:GetCallerIdentity"], resources=["*"]))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["eks:DescribeCluster"],
            resources=[f"arn:aws:eks:{self.region}:{self.account}:cluster/fleetpulse-eks-cluster"],
        ))

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

        # Deploy project: rolls the EKS cluster to the commit-SHA images built above (kubectl via aws-auth mapping)
        deploy_project = codebuild.PipelineProject(
            self, "FleetPulseDeployProject",
            project_name="fleetpulse-deploy",
            role=build_role,
            environment=codebuild.BuildEnvironment(build_image=codebuild.LinuxBuildImage.STANDARD_7_0),
            environment_variables={
                "CLUSTER_NAME": codebuild.BuildEnvironmentVariable(value="fleetpulse-eks-cluster"),
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec-deploy.yml")
        )

        # 4. Pipeline Definition using POLL trigger to avoid webhook creation error
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
                            oauth_token=github_token_secret.secret_value_from_json("token"),
                            trigger=codepipeline_actions.GitHubTrigger.POLL,
                            output=source_output
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Test_Build_Scan_Push",
                            project=build_project,
                            input=source_output,
                            outputs=[build_output],
                            variables_namespace="BuildVars",
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Rollout_To_EKS",
                            project=deploy_project,
                            input=source_output,
                            environment_variables={
                                # Immutable commit-SHA tag exported by the Build stage
                                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(
                                    value="#{BuildVars.IMAGE_TAG}",
                                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                                ),
                            },
                        )
                    ]
                )
            ]
        )

        # 5. cdk-nag Compliance Suppressions
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-S1", "reason": "Access logging optional for pipeline artifact bucket."},
            {"id": "AwsSolutions-IAM5", "reason": "CodeBuild ECR push permissions require wildcard image tags."},
            {"id": "AwsSolutions-CB4", "reason": "Service-managed encryption used for CodeBuild logs in PoC environment."},
            {"id": "AwsSolutions-IAM5", "reason": "Wildcards limited to ECR auth token, STS identity and CodeBuild report/log groups.", "appliesTo": ["Resource::*"]},
        ])