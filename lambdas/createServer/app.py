import os
import boto3
import json
import uuid
from botocore.exceptions import ClientError

# ENV: GLOBAL_REGION, REGION, EFS_PATH 

def lambda_handler(event, context):
    user_email = event["owner"]
    server_type = event["type"]
    version = event["version"]
    region = event["region"] #TODO change to ENV REGION

    server_uuid = str(uuid.uuid4())

    # Clients
    ssm = boto3.client('ssm', region_name=os.environ["GLOBAL_REGION"])
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["GLOBAL_REGION"])
    s3 = boto3.client("s3", region_name=os.environ["GLOBAL_REGION"])

    # Fetch table and bucket names from SSM
    table_name = ssm.get_parameter(Name="/global/dynamo/table-name")['Parameter']['Value']
    bucket_name = ssm.get_parameter(Name="/global/s3/minecraft-versions/id")['Parameter']['Value']

    # Create Config Profile in DynamoDB
    table = dynamodb.Table(table_name)
    config_item = {
        "PK": f"USERS#{user_email}",
        "SK": "CONFIGPROFILE",
        "ServerUUID": server_uuid,
        "Type": server_type,
        "Version": version,
        "Region": region,
        "ServerName": f"minecraft-{server_uuid[:8]}"
    }

    try:
        table.put_item(Item=config_item)
        print(f"Created DynamoDB config profile: {server_uuid}")
    except ClientError as e:
        print(f"Error writing to DynamoDB: {e}")

    # EFS path
    efs_path = os.environ.get("EFS_PATH", "/mnt/efs")
    server_path = f"{efs_path}/{server_uuid}"

    try:
        os.makedirs(server_path, exist_ok=True)
        print(f"Created EFS directory: {server_path}")
    except Exception as e:
        print("Failed to create EFS directory: {e}")

    # Create eula.txt
    try:
        eula_path = os.path.join(server_path, "eula.txt")
        with open(eula_path, "w") as f:
            f.write("eula=true\n")
        print(f"Created EULA file at {eula_path}")
    except Exception as e:
        print("Failed to create eula.txt: {e}")

    # Download server.jar from S3
    s3_key = f"{version}/server.jar"
    dest_path = f"{server_path}/server.jar"

    try:
        s3.download_file(bucket_name, s3_key, dest_path)
        print(f"Downloaded {s3_key} -> {dest_path}")
    except ClientError as e:
        print("Failed to download server.jar: {e}")

    print(f"serverUUID {server_uuid}, Server profile created and jar prepared at {server_path}")