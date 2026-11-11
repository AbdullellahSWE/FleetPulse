import aws_cdk as core
import aws_cdk.assertions as assertions

from fleet_pulse.fleet_pulse_stack import FleetPulseStack

# example tests. To run these tests, uncomment this file along with the example
# resource in fleet_pulse/fleet_pulse_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = FleetPulseStack(app, "fleet-pulse")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
