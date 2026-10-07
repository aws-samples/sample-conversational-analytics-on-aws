# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""QuickSight Chat Agent Stack - Amazon Quick custom chat agent.

This stack creates a QuickSight (Amazon Quick / Quick Suite) custom chat agent
that answers natural language questions about AnyCompany Bank's Cards domain, using the
persona instructions in ``quicksight/chat-agent-prompt.md``.

NATIVE AGENT, CUSTOM-RESOURCE PERMISSIONS:
    The agent itself is a native ``AWS::QuickSight::Agent`` (``quicksight.CfnAgent``),
    so CloudFormation owns create / update / delete. That resource type has no
    permissions property, so sharing still goes through an ``AwsCustomResource``
    calling ``UpdateAgentPermissions``.

    ``install_latest_aws_sdk=True`` is REQUIRED on that custom resource: the SDK
    bundled in the custom resource Lambda predates the Agent API, so we npm-install
    the latest ``@aws-sdk/client-quicksight`` at deploy time. If this ever fails
    (e.g. the Lambda has no egress to npm), the call will report an unknown action.

    Upgrading from the old custom-resource agent: earlier versions created the
    agent with an ``AwsCustomResource`` using the same ``AgentId``. CloudFormation
    creates the new resource before deleting the old one, so an in-place update
    fails with a conflict. Destroy this stack first, then deploy.

WHY NO SPACE (deliberate):
    The Agent API accepts a ``Spaces`` list to scope an agent to specific data
    resources (Topics/DataSets). We tried this and it BREAKS chat: any agent
    with an API-attached Space fails at chat time with a generic 400 / the
    console shows the knowledge resource as "resource unavailable" /
    RESOURCE_NOT_FOUND. This was reproduced with BOTH a stack-created space and
    a known-good console-created space, so the problem is the API's
    agent<->space binding, not the space itself: ``CreateAgent`` records the
    space ARN but does not register the binding in the backing Q Business layer
    (the service-injected ``QbsAwsAccountId`` / ``ModelProfileId``), which the
    console wires up separately. Until AWS closes that gap, we create the agent
    WITHOUT a Space. Like the console-created agents, it answers over whatever
    Q Topics / datasets the invoking user can access - which for this sample includes
    the deployed topics. DO NOT re-add ``Spaces`` here without re-testing chat.

Prerequisites:
- ConversationalAnalytics-QuickSight stack deployed (creates the Group referenced for permissions)

Deployment:
    uv run cdk deploy ConversationalAnalytics-QuickSight-ChatAgent

Compliance note: all data is synthetic. If you adapt this sample to real EU personal data
or payment card data, you are responsible for GDPR, PCI DSS and other applicable requirements.
"""

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Fn
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_quicksight as quicksight
from aws_cdk import custom_resources as cr
from cdk_nag import NagSuppressions
from constructs import Construct

# Agent identity constants. AgentId pattern is [0-9a-zA-Z-_.+]+ (underscores OK,
# unlike physical-table-map keys). Name max length is 50 chars.
AGENT_ID = "conversational-analytics-cards-chat-agent"
AGENT_NAME = "Cards Analyst"
AGENT_DESCRIPTION = (
    "Data analyst for AnyCompany Bank's Cards domain. Answers questions about "
    "transactions, chargebacks, tokenizations, cards, customers, and merchants."
)
WELCOME_MESSAGE = (
    "Hi! Ask me about chargebacks, tokenization timing, customer spending, "
    "card delivery, campaigns, or customer profiles."
)
# Max 3 starter prompts, each <= 100 chars. Drawn from the 6 demo use cases.
STARTER_PROMPTS = [
    "Why did chargebacks increase in the week of January 15th, 2026?",
    "How long after joining should we push users to tokenize their cards?",
    "What type of merchants do our best customers prefer?",
]

# Persona instructions live in versioned markdown files and are loaded at synth.
# The persona prompt tells the agent to "refer to the Business Context" for the
# Athena schema and JOIN paths, so both files are concatenated into a single set
# of CustomInstructions.
QUICKSIGHT_DIR = Path(__file__).parent.parent.parent / "quicksight"
PERSONA_FILE = QUICKSIGHT_DIR / "chat-agent-prompt.md"
CONTEXT_FILE = QUICKSIGHT_DIR / "chat-agent-context.md"


class QuickSightChatAgentStack(cdk.Stack):
    """QuickSight custom chat agent stack for Conversational Analytics.

    Creates:
    - A custom chat agent (native AWS::QuickSight::Agent)
    - Agent permissions for the QuickSight user and the conversational-analytics-demo group
      (via AwsCustomResource -> quicksight:UpdateAgentPermissions)

    Prerequisites:
    - QuickSightStack deployed (exports the group ARN as ConversationalAnalytics-QuickSightGroup)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        quicksight_user_arn: str,
        quicksight_namespace: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.quicksight_user_arn = quicksight_user_arn
        self.quicksight_namespace = quicksight_namespace

        # Group ARN exported by the QuickSight DataSets stack.
        self.quicksight_group_arn = Fn.import_value("ConversationalAnalytics-QuickSightGroup")

        self.persona_instructions = self._load_persona()

        self._create_custom_resource_log_group()
        self._create_custom_resource_role()
        self._create_chat_agent()
        self._grant_agent_permissions()
        self._create_outputs()

        # The AwsCustomResource provider Lambda is created and versioned by aws-cdk-lib
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.stack_name}/AWS679f53fac002430cb0da5b7982bd2287/Resource",
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Runtime of the CDK-managed AwsCustomResource provider is set by aws-cdk-lib; it follows CDK upgrades.",
                }
            ],
        )

    def _load_persona(self) -> str:
        """Load persona instructions + business context from markdown files.

        The persona prompt references the business context (Athena schema, JOIN
        paths) as the agent's SQL fallback reference, so both files are
        concatenated into a single CustomInstructions string.

        The Agent API accepts 5..350000 chars for CustomInstructions.
        """
        parts = []
        for label, path in (("persona", PERSONA_FILE), ("context", CONTEXT_FILE)):
            if not path.exists():
                raise FileNotFoundError(
                    f"Chat agent {label} file not found: {path}"
                )
            parts.append(path.read_text(encoding="utf-8").strip())

        text = "\n\n---\n\n".join(parts)
        if len(text) < 5:
            raise ValueError("Chat agent instructions are empty")
        if len(text) > 350000:
            raise ValueError(
                f"Chat agent instructions exceed the 350000-char API limit "
                f"({len(text)} chars)"
            )
        return text


    def _create_custom_resource_log_group(self) -> None:
        """Log group for the shared AwsCustomResource Lambda.

        Without this the Lambda's log group never expires and survives ``cdk destroy``.
        """
        self.custom_resource_log_group = logs.LogGroup(
            self,
            "CustomResourceLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

    def _create_custom_resource_role(self) -> None:
        """IAM role for the custom resource that manages agent permissions."""
        agent_resource = f"arn:aws:quicksight:{self.region}:{self.account}:agent/{AGENT_ID}"
        self.custom_resource_role = iam.Role(
            self,
            "ChatAgentCustomResourceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "ChatAgentPolicy": iam.PolicyDocument(
                    statements=[
                        # Write logs only to this stack's custom-resource log group
                        # (replaces the AWSLambdaBasicExecutionRole managed policy)
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[self.custom_resource_log_group.log_group_arn],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "quicksight:UpdateAgentPermissions",
                                "quicksight:DescribeAgentPermissions",
                            ],
                            resources=[agent_resource],
                        ),
                    ]
                )
            },
        )

    def _create_chat_agent(self) -> None:
        """Create the chat agent as a native AWS::QuickSight::Agent.

        Created WITHOUT a Space - see module docstring.
        """
        self.chat_agent = quicksight.CfnAgent(
            self,
            "ChatAgent",
            aws_account_id=self.account,
            agent_id=AGENT_ID,
            name=AGENT_NAME,
            description=AGENT_DESCRIPTION,
            agent_lifecycle="PUBLISHED",
            welcome_message=WELCOME_MESSAGE,
            starter_prompts=STARTER_PROMPTS,
            custom_prompt_input=quicksight.CfnAgent.CustomPromptInputProperty(
                new_prompt=quicksight.CfnAgent.CustomPromptInputParametersProperty(
                    custom_instructions=self.persona_instructions,
                )
            ),
        )

    def _grant_agent_permissions(self) -> None:
        """Grant owner permissions to the user and viewer permissions to the group.

        Agents accept User or Group ARNs as principals (like Topics/DataSets),
        not Namespace ARNs.
        """
        agent_owner_actions = [
            "quicksight:DescribeAgent",
            "quicksight:UpdateAgent",
            "quicksight:DeleteAgent",
            "quicksight:DescribeAgentPermissions",
            "quicksight:UpdateAgentPermissions",
        ]

        permissions = [
            {"Principal": self.quicksight_user_arn, "Actions": agent_owner_actions},
            {"Principal": self.quicksight_group_arn, "Actions": ["quicksight:DescribeAgent"]},
        ]

        self.agent_permissions = cr.AwsCustomResource(
            self,
            "ChatAgentPermissions",
            on_create=cr.AwsSdkCall(
                service="QuickSight",
                action="updateAgentPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "AgentId": AGENT_ID,
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-chat-agent-permissions"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="QuickSight",
                action="updateAgentPermissions",
                parameters={
                    "AwsAccountId": self.account,
                    "AgentId": AGENT_ID,
                    "GrantPermissions": permissions,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "conversational-analytics-chat-agent-permissions"
                ),
            ),
            # No on_delete - permissions are removed when the agent is deleted.
            install_latest_aws_sdk=True,
            role=self.custom_resource_role,
            log_group=self.custom_resource_log_group,
        )

        self.agent_permissions.node.add_dependency(self.chat_agent)

    def _create_outputs(self) -> None:
        """CloudFormation outputs."""
        cdk.CfnOutput(
            self,
            "ChatAgentId",
            value=AGENT_ID,
            description="QuickSight custom chat agent ID",
            export_name="ConversationalAnalytics-QuickSightChatAgentId",
        )
        cdk.CfnOutput(
            self,
            "ChatAgentArn",
            value=self.chat_agent.attr_arn,
            description="QuickSight custom chat agent ARN",
            export_name="ConversationalAnalytics-QuickSightChatAgentArn",
        )
