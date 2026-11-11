from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_kinesis as kinesis,
    aws_kinesisfirehose as kinesisfirehose,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_iam as iam,
)
from cdk_nag import NagSuppressions
from constructs import Construct

class StreamingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Kinesis Data Stream for high-frequency EV telemetry ingestion
        self.telemetry_stream = kinesis.Stream(
            self, "TelemetryDataStream",
            shard_count=4,
            retention_period=Duration.hours(24)
        )

        # 2. S3 Bucket for raw telemetry batch archiving with SSL enforced
        self.archive_bucket = s3.Bucket(
            self, "TelemetryArchiveBucket",
            bucket_name=f"fleetpulse-telemetry-archive-{self.account}-{self.region}",
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 3. Kinesis Firehose Delivery Stream for S3 archiving
        firehose_role = iam.Role(
            self, "FirehoseDeliveryRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com")
        )
        self.archive_bucket.grant_read_write(firehose_role)
        self.telemetry_stream.grant_read(firehose_role)

        # Explicitly grant DescribeStream permissions required by Firehose validation
        firehose_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kinesis:DescribeStream"],
                resources=[self.telemetry_stream.stream_arn]
            )
        )

        self.firehose_delivery_stream = kinesisfirehose.CfnDeliveryStream(
            self, "TelemetryFirehose",
            delivery_stream_name="fleetpulse-telemetry-firehose",
            delivery_stream_type="KinesisStreamAsSource",
            kinesis_stream_source_configuration=kinesisfirehose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
                kinesis_stream_arn=self.telemetry_stream.stream_arn,
                role_arn=firehose_role.role_arn
            ),
            extended_s3_destination_configuration=kinesisfirehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.archive_bucket.bucket_arn,
                role_arn=firehose_role.role_arn,
                buffering_hints=kinesisfirehose.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=300,
                    size_in_m_bs=5
                ),
                compression_format="GZIP"
            )
        )

        # 4. SQS Queue & Dead Letter Queue (DLQ) for dispatch event handling with SSL enforced
        dlq = sqs.Queue(
            self, "DispatchDLQ",
            queue_name="fleetpulse-dispatch-dlq",
            enforce_ssl=True
        )
        self.dispatch_queue = sqs.Queue(
            self, "DispatchQueue",
            queue_name="fleetpulse-dispatch-queue",
            enforce_ssl=True,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=5, queue=dlq)
        )

        # 5. SNS Topic for critical vehicle alerts with enforced SSL policy
        self.alert_topic = sns.Topic(self, "VehicleAlertTopic", topic_name="fleetpulse-vehicle-alerts")
        self.alert_topic.add_subscription(subs.SqsSubscription(self.dispatch_queue))
        self.alert_topic.add_to_resource_policy(
            iam.PolicyStatement(
                sid="EnforcePublishSSL",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["sns:Publish"],
                resources=[self.alert_topic.topic_arn],
                conditions={"Bool": {"aws:SecureTransport": "false"}}
            )
        )

        # 6. Step Functions State Machine for automated dispatch workflows
        sfn_log_group = logs.LogGroup(
            self, "SfnLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        pass_state = sfn.Pass(self, "ProcessTelemetryEvent", comment="Process EV Diagnostics")
        publish_task = tasks.SnsPublish(
            self, "PublishAlert",
            topic=self.alert_topic,
            message=sfn.TaskInput.from_json_path_at("$.alert_message")
        )
        
        definition = pass_state.next(publish_task)
        self.state_machine = sfn.StateMachine(
            self, "TelemetryDispatchWorkflow",
            state_machine_name="fleetpulse-dispatch-workflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            logs=sfn.LogOptions(
                destination=sfn_log_group,
                level=sfn.LogLevel.ALL
            ),
            tracing_enabled=True,
            timeout=Duration.minutes(5)
        )

        # cdk-nag Security & Compliance Suppressions
        NagSuppressions.add_stack_suppressions(self, [
            {"id": "AwsSolutions-S1", "reason": "Access logging optional for PoC archive bucket."},
            {"id": "AwsSolutions-IAM5", "reason": "Firehose S3 write permissions require wildcard bucket scoping."},
            {"id": "AwsSolutions-KDS3", "reason": "AWS managed KMS key used for Kinesis stream encryption to optimize costs."},
            {"id": "AwsSolutions-KDF1", "reason": "Firehose with KinesisStreamAsSource relies on Kinesis Data Stream encryption."},
        ])