import boto3
import os
from botocore.exceptions import ClientError
import shutil

# ENV: GLOBAL_REGION, EFS_PATH

def lambda_handler(event, context):
    user_email = event.get("owner")

    # Clients
    ssm = boto3.client('ssm', region_name=os.environ["GLOBAL_REGION"])
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["GLOBAL_REGION"])

    # Table
    table_name = ssm.get_parameter(Name="/global/dynamo/table-name")['Parameter']['Value']
    table = dynamodb.Table(table_name)

    server_item = {
        "PK": f"USERS#{user_email}",
        "SK": "SERVER",
        "status": "DELETING"
    }

    try:
        table.put_item(Item=server_item)
    except ClientError as e:
        print(f"Error writing to DynamoDB: {e}")


    #Get CONFIGPROFILE
    response = table.get_item(Key={"PK": f"USERS#{user_email}", "SK": f"CONFIGPROFILE"})
    configprofile = response.get("Item")
    server_uuid = configprofile.get('ServerUUID')
    table.delete_item(Key={"PK": f"USERS#{user_email}", "SK": f"CONFIGPROFILE"})
    table.delete_item(Key={"PK": f"USERS#{user_email}", "SK": f"SERVER"})

    # EFS path
    efs_path = os.environ.get("EFS_PATH", "/mnt/efs")
    server_path = f"{efs_path}/{server_uuid}"

    try:
        #SUDO DELETE server_path
        if os.path.exists(server_path):
            shutil.rmtree(server_path, ignore_errors=True)
    except ClientError as e:
        print(f"Failed to delete EFS folder: {e}")