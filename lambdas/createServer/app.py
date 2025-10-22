import boto3
import base64
import random
import uuid
import json
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    try:
        message = event['Records'][0]['body']
        if isinstance(message, str):
            event_data = json.loads(message)
        else:
            event_data = message
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing SQS message: {e}")
        return {
            'statusCode': 400,
            'body': f'Invalid SQS message: {e}'
        }

    # Event variables
    region = event_data['region']
    server_version = event_data['version']
    server_type = event_data['type']
    server_owner = event_data['ownerUUID']
    server_flags = getFlags(server_type)

    # Servicess
    ec2 = boto3.client('ec2', region_name=region)
    ssm = boto3.client('ssm', region_name=region)
    dynamodb = boto3.resource('dynamodb', region_name=region)

    # Get EFS, SG, Subnet, S3, VPC
    efs_id = ssm.get_parameter(Name=f"/efs/{region}/id")['Parameter']['Value']
    security_groups = [ssm.get_parameter(Name=f"/sg/{region}/id")['Parameter']['Value']]
    subnet = getSubnet(region)
    minecraft_jars = ssm.get_parameter(Name="/s3/minecraft-versions/id")['Parameter']['Value']

    # Get latest Amazon Linux 2023 AMI
    image_id = get_latest_ami(region)

    # Check DynamoDB for existing server
    table = dynamodb.Table('ServerRegistry')
    serverUUID = get_or_create_server_uuid(table, server_owner)

    # Build user data
    user_data = f"""#!/bin/bash
    set -euxo pipefail
    dnf install -y amazon-efs-utils java-21-amazon-corretto aws-cli
    mkdir -p /mnt/efs
    mount -t efs -o tls {efs_id}:/ /mnt/efs/
    cd /mnt/efs

    if [ ! -d {serverUUID} ]; then
        mkdir {serverUUID}
        cd {serverUUID}
        aws s3 cp s3://{minecraft_jars}/{server_version}/server.jar .
        echo "eula=true" > eula.txt
        chown ec2-user:ec2-user server.jar eula.txt
    else
        cd {serverUUID}
    fi

    java {server_flags} -jar server.jar nogui
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
        'UserData': user_data
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
        case "t3.large":
            return "-Xms2G -Xmx4G"
        case "t3.xlarge":
            return "-Xms4G -Xmx8G"
        case "t3.2xlarge":
            return "-Xms8G -Xmx16G"
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


def get_or_create_server_uuid(table, server_owner: str):
    # Try to fetch from DynamoDB
    response = table.get_item(Key={'server_name': server_owner})
    if 'Item' in response:
        return response['Item']['serverUUID']

    # Otherwise create one
    serverUUID = str(uuid.uuid4())
    table.put_item(Item={
        'server_name': server_owner,
        'serverUUID': serverUUID
    })
    return serverUUID
