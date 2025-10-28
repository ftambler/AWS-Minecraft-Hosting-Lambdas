import os
import boto3
from botocore.exceptions import ClientError

# ENV GLOBAL_REGION, EFS_IF, SECURITY_GROUP_ID, SUBNET_ID

def lambda_handler(event, context):
    user_email = event["owner"]

    # Clients
    ssm = boto3.client('ssm', region_name=os.environ["GLOBAL_REGION"])
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["GLOBAL_REGION"])
    ec2 = boto3.client('ec2', region_name=region)

    # Table
    table_name = ssm.get_parameter(Name="/global/dynamo/table-name")['Parameter']['Value']
    table = dynamodb.Table(table_name)

    response = table.get_item(
        Key={
            "PK": f"USERS#{user_email}",
            "SK": f"CONFIGPROFILE"
        }
    )
    config = response.get("Item")

    # Config Profile variables
    region = config.get('Region')
    serverUUID = config.get('ServerUUID')
    server_type = config.get('Type')
    server_flags = getFlags(server_type)

    # Get EFS, SG, Subnet, S3, VPC
    efs_id = os.getenv('EFS_ID')
    security_groups = [os.getenv('SECURITY_GROUP_ID')]
    subnet = os.getenv("SUBNET_ID")

    # Get latest Amazon Linux 2023 AMI
    image_id = get_latest_ami(region)

    # Build user data
    user_data = f"""#!/bin/bash
        set -euxo pipefail

        # Install dependencies
        dnf install -y amazon-efs-utils java-21-amazon-corretto aws-cli

        # Mount EFS
        mkdir -p /mnt/efs
        mount -t efs -o tls {efs_id}:/ /mnt/efs/

        # Make sure everything under the server folder is writable
        chmod -R 777 /mnt/efs/{serverUUID} || true

        # Go into that folder and start the Minecraft server
        cd /mnt/efs/{serverUUID}

        # Delete stale lock if any
        rm -f world/session.lock || true

        # Start as ec2-user (not root)
        sudo -u ec2-user java {server_flags} -jar server.jar nogui
        """

    # Launch EC2 instance
    instance_params = {
        'ImageId': image_id,
        'InstanceType': server_type,
        'MinCount': 1,
        'MaxCount': 1,
        'NetworkInterfaces': [{
            'SubnetId': subnet,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': security_groups
        }],
        'UserData': user_data,
        'IamInstanceProfile': {
            'Name': "EC2ServerInstanceProfile"
        },
        'TagSpecifications': [
        {
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': serverUUID},
                {'Key': 'serverOwner', 'Value': user_email}
            ]
        }
        ]
    }

    try:
        response = ec2.run_instances(**instance_params)
        instance_id = response['Instances'][0]['InstanceId']

        # Wait until running and get IP
        ec2_resource = boto3.resource('ec2', region_name=region)
        instance = ec2_resource.Instance(instance_id)
        instance.wait_until_running()
        instance.load()
        public_ip = instance.public_ip_address

        table.put_item(Item={
            "PK": f"USERS#{user_email}",
            "SK": f"SERVER#{serverUUID}",
            "InstanceId": instance_id,
            "Region": region,
            "PublicIp": instance.public_ip_address,
            "LaunchedAt": instance.launch_time.isoformat()
        })

        return {
            'statusCode': 200,
            'body': {
                'instance_id': instance_id,
                'public_ip': public_ip,
                'serverUUID': serverUUID
            }
        }
    except Exception as e:
        print(f"Error launching EC2 instance: {e}")
        return {
            'statusCode': 500,
            'body': f'Error launching EC2 instance: {e}'
        }


def getFlags(server_type: str):
    match server_type:
        case "t2.small":
            return "-Xms512M -Xmx1G"
        case "t2.medium":
            return "-Xms1G -Xmx2G"
        case "t2.large":
            return "-Xms2G -Xmx4G"
        case _:
            return "-Xms1G -Xmx2G"


def getSubnet(region: str):
    ec2 = boto3.client("ec2", region_name=region)
    ssm = boto3.client("ssm", region_name=region)

    subnet_param = f"/subnet/{region}/id"

    try:
        subnet_id = ssm.get_parameter(Name=subnet_param)["Parameter"]["Value"]
    except ClientError as e:
        raise RuntimeError(f"Failed to get Subnet ID from SSM ({subnet_param}): {e}")

    # Validate the subnet actually exists in this region
    try:
        response = ec2.describe_subnets(SubnetIds=[subnet_id])
        subnets = response.get("Subnets", [])
    except ClientError as e:
        raise RuntimeError(f"Failed to describe Subnets: {e}")

    if not subnets:
        raise RuntimeError(f"Subnet not found: {subnet_id} in {region}")

    return subnet_id


def get_latest_ami(region: str):
    ssm = boto3.client('ssm', region_name=region)
    # AWS publishes a parameter for the latest Amazon Linux 2023 AMI
    param = ssm.get_parameter(Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64")
    return param['Parameter']['Value']