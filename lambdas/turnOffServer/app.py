import boto3
import os

# ENV: REGION, GLOBAL_REGION

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name=os.environ["REGION"])
    ssm = boto3.client('ssm', region_name=os.environ["GLOBAL_REGION"])
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["GLOBAL_REGION"])

    table_name = ssm.get_parameter(Name="/global/dynamo/table-name")['Parameter']['Value']
    table = dynamodb.Table(table_name)

    user_email = event.get('owner')

    response = table.get_item(
        Key={
            "PK": f"USERS#{user_email}",
            "SK": f"SERVER"
        }
    )
    server = response.get("Item")
    instance_id = server.get('InstanceId')

    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        print(f"Stopping instance {instance_id}...")
        table.delete_item(
            Key={
                "PK": f"USERS#{user_email}",
                "SK": f"SERVER"
            }
        )
    except Exception as e:
        print(f"Error stopping instance {instance_id}: {e}")