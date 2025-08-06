#!/usr/bin/env python3

from aws_cdk import (
    App,
    Stack,
    Duration,
    RemovalPolicy,
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_kms as kms,
    CfnOutput,
)
from constructs import Construct


class MSKEKSPubSubStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the environment from context, default to "dev" if not provided
        env_postfix = self.node.try_get_context("env") or "dev"

        # Create VPC for MSK cluster
        vpc = ec2.Vpc(
            self,
            id=f"MSKVpc-{env_postfix}",
            max_azs=3,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="PublicSubnet",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="PrivateSubnet",
                    cidr_mask=24,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Create KMS key for encryption
        kms_key = kms.Key(
            self,
            id=f"MSKEncryptionKey-{env_postfix}",
            description="KMS key for MSK cluster encryption",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create security group for MSK cluster
        msk_security_group = ec2.SecurityGroup(
            self,
            id=f"MSKSecurityGroup-{env_postfix}",
            vpc=vpc,
            description="Security group for MSK cluster",
            allow_all_outbound=True,
        )

        # Create security group for EKS clients
        eks_client_security_group = ec2.SecurityGroup(
            self,
            id=f"EKSClientSecurityGroup-{env_postfix}",
            vpc=vpc,
            description="Security group for EKS applications connecting to MSK",
            allow_all_outbound=True,
        )

        # Allow EKS clients to connect to MSK on Kafka ports
        msk_security_group.add_ingress_rule(
            peer=eks_client_security_group,
            connection=ec2.Port.tcp(9092),  # PLAINTEXT
            description="Kafka PLAINTEXT from EKS",
        )
        msk_security_group.add_ingress_rule(
            peer=eks_client_security_group,
            connection=ec2.Port.tcp(9094),  # TLS
            description="Kafka TLS from EKS",
        )
        msk_security_group.add_ingress_rule(
            peer=eks_client_security_group,
            connection=ec2.Port.tcp(9096),  # SASL_SSL
            description="Kafka SASL_SSL from EKS",
        )
        msk_security_group.add_ingress_rule(
            peer=eks_client_security_group,
            connection=ec2.Port.tcp(2181),  # Zookeeper
            description="Zookeeper from EKS",
        )

        # Allow communication within MSK security group
        msk_security_group.add_ingress_rule(
            peer=msk_security_group,
            connection=ec2.Port.all_traffic(),
            description="MSK internal communication",
        )

        # Create CloudWatch log group for MSK
        log_group = logs.LogGroup(
            self,
            id=f"MSKLogGroup-{env_postfix}",
            log_group_name="/aws/msk/cluster-logs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create MSK cluster configuration
        cluster_config = msk.CfnConfiguration(
            self,
            id=f"MSKClusterConfig-{env_postfix}",
            name="msk-eks-pubsub-config",
            description="MSK configuration for EKS pub/sub system",
            kafka_versions_list=["3.5.1"],
            server_properties="""
# Message size configuration
message.max.bytes=10485760
replica.fetch.max.bytes=10485760

# Performance tuning
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log retention
log.retention.hours=168
log.retention.bytes=1073741824
log.segment.bytes=1073741824

# Replication
default.replication.factor=3
min.insync.replicas=2

# Auto topic creation
auto.create.topics.enable=true
num.partitions=6

# Compression
compression.type=snappy
""",
        )

        # Create MSK cluster
        # Calculate number of broker nodes based on the number of AZs
        # Must be a multiple of the number of AZs
        num_azs = len(vpc.private_subnets)
        number_of_brokers = num_azs * 2  # Using 2 brokers per AZ for better redundancy

        msk_cluster = msk.CfnCluster(
            self,
            id=f"MSKCluster-{env_postfix}",
            cluster_name="eks-pubsub-cluster",
            kafka_version="3.5.1",
            number_of_broker_nodes=number_of_brokers,
            broker_node_group_info=msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type="kafka.m5.large",
                client_subnets=[
                    subnet.subnet_id for subnet in vpc.private_subnets
                ],
                security_groups=[msk_security_group.security_group_id],
                storage_info=msk.CfnCluster.StorageInfoProperty(
                    ebs_storage_info=msk.CfnCluster.EBSStorageInfoProperty(
                        volume_size=100,
                    )
                ),
            ),
            client_authentication=msk.CfnCluster.ClientAuthenticationProperty(
                unauthenticated=msk.CfnCluster.UnauthenticatedProperty(enabled=True)
            ),
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=cluster_config.attr_arn,
                revision=1,
            ),
            encryption_info=msk.CfnCluster.EncryptionInfoProperty(
                encryption_at_rest=msk.CfnCluster.EncryptionAtRestProperty(
                    data_volume_kms_key_id=kms_key.key_id
                ),
                encryption_in_transit=msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker="TLS",
                    in_cluster=True,
                ),
            ),
            enhanced_monitoring="PER_TOPIC_PER_BROKER",
            logging_info=msk.CfnCluster.LoggingInfoProperty(
                broker_logs=msk.CfnCluster.BrokerLogsProperty(
                    cloud_watch_logs=msk.CfnCluster.CloudWatchLogsProperty(
                        enabled=True,
                        log_group=log_group.log_group_name,
                    ),
                    firehose=msk.CfnCluster.FirehoseProperty(enabled=False),
                    s3=msk.CfnCluster.S3Property(enabled=False),
                )
            ),
            open_monitoring=msk.CfnCluster.OpenMonitoringProperty(
                prometheus=msk.CfnCluster.PrometheusProperty(
                    jmx_exporter=msk.CfnCluster.JmxExporterProperty(
                        enabled_in_broker=True
                    ),
                    node_exporter=msk.CfnCluster.NodeExporterProperty(
                        enabled_in_broker=True
                    ),
                )
            ),
        )

        # Create IAM role for EKS pods to access MSK
        eks_msk_role = iam.Role(
            self,
            id=f"EKSMSKRole-{env_postfix}",
            assumed_by=iam.ServicePrincipal("pods.eks.amazonaws.com"),
            description="IAM role for EKS pods to access MSK",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonMSKReadOnlyAccess")
            ],
        )

        # Add additional permissions for MSK operations
        eks_msk_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kafka:CreateTopic",
                    "kafka:DeleteTopic",
                    "kafka:DescribeCluster",
                    "kafka:DescribeClusterV2",
                    "kafka:GetBootstrapBrokers",
                    "kafka-cluster:Connect",
                    "kafka-cluster:AlterCluster",
                    "kafka-cluster:DescribeCluster",
                    "kafka-cluster:WriteData",
                    "kafka-cluster:ReadData",
                    "kafka-cluster:AlterGroup",
                    "kafka-cluster:DescribeGroup",
                    "kafka-cluster:DescribeTopic",
                    "kafka-cluster:AlterTopic",
                    "kafka-cluster:CreateTopic",
                    "kafka-cluster:DeleteTopic",
                ],
                resources=[msk_cluster.attr_arn, f"{msk_cluster.attr_arn}/*"],
            )
        )

        # Outputs
        CfnOutput(
            self,
            id=f"MSKClusterArn-{env_postfix}",
            value=msk_cluster.attr_arn,
            description="MSK Cluster ARN",
            export_name=f"MSKClusterArn-{env_postfix}",
        )

        CfnOutput(
            self,
            id=f"MSKClusterName-{env_postfix}",
            value=msk_cluster.cluster_name,
            description="MSK Cluster Name",
            export_name=f"MSKClusterName-{env_postfix}",
        )

        CfnOutput(
            self,
            id="VPCId-{env_postfix}",
            value=vpc.vpc_id,
            description="VPC ID for MSK cluster",
            export_name=f"MSKVPCId-{env_postfix}",
        )

        CfnOutput(
            self,
            id=f"EKSClientSecurityGroupId-{env_postfix}",
            value=eks_client_security_group.security_group_id,
            description="Security Group ID for EKS clients",
            export_name=f"EKSClientSecurityGroupId-{env_postfix}",
        )

        CfnOutput(
            self,
            id=f"EKSMSKRoleArn-{env_postfix}",
            value=eks_msk_role.role_arn,
            description="IAM Role ARN for EKS pods to access MSK",
            export_name=f"EKSMSKRoleArn-{env_postfix}",
        )

        CfnOutput(
            self,
            id=f"PrivateSubnetIds-{env_postfix}",
            value=",".join([subnet.subnet_id for subnet in vpc.private_subnets]),
            description="Private subnet IDs where MSK is deployed",
            export_name=f"MSKPrivateSubnetIds-{env_postfix}",
        )


# App entry point
app = App()
MSKEKSPubSubStack(app, "MSKEKSPubSubStack")
app.synth()
