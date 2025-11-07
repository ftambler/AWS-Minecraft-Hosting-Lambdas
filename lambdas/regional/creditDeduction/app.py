import boto3
import json
import os
from botocore.exceptions import ClientError

# ENV: GLOBAL_REGION, TURN_OFF_LAMBDA_NAME

dynamodb = boto3.resource("dynamodb", region_name=os.environ["GLOBAL_REGION"])
lambda_client = boto3.client("lambda", region_name=os.environ["GLOBAL_REGION"])
ssm = boto3.client("ssm", region_name=os.environ["GLOBAL_REGION"])
# Dynamo
table_name = ssm.get_parameter(Name="/global/dynamo/table-name")["Parameter"]["Value"]
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    owner = event["owner"]
    instance_type = event["instanceType"]

    # Fetch user profile
    try:
        response = table.get_item(Key={"PK": f"USERS#{owner}", "SK": "PROFILE"})
        profile = response.get("Item")
        if not profile:
            raise ValueError(f"Profile not found for {owner}")
    except ClientError as e:
        print(f"DynamoDB get_item error: {e}")
        return {"statusCode": 500, "body": "Error reading profile"}

    name = profile.get("Name", "")
    credits = profile.get("Credits", 0)

    # Deduct credits
    deduction = calculate_deduction(instance_type)
    new_credits = max(0, credits - deduction)

    # Update record
    try:
        table.update_item(
            Key={"PK": f"USERS#{owner}", "SK": "PROFILE"},
            UpdateExpression="SET Credits = :new",
            ExpressionAttributeValues={":new": new_credits},
        )
    except ClientError as e:
        print(f"DynamoDB update error: {e}")
        return {"statusCode": 500, "body": "Error updating credits"}

    # If credits exhausted, trigger server shutdown
    if new_credits == 0:
        try:
            lambda_client.invoke(
                FunctionName=os.environ["TURN_OFF_LAMBDA_NAME"],
                InvocationType="Event",
                Payload=json.dumps({"owner": owner}),
            )
        except ClientError as e:
            print(f"Error invoking turnOffServer: {e}")

    return {
        "statusCode": 200,
        "body": {
            "owner": owner,
            "name": name,
            "oldCredits": credits,
            "deducted": deduction,
            "newCredits": new_credits,
        },
    }


def calculate_deduction(instance_type: str) -> int:
    """Return credits to deduct per 10-minute interval."""
    response = table.get_item(Key={"PK": "GLOBAL", "SK": "RESOURCES"})
    item = response.get("Item")

    if not item or "types" not in item:
        return None

    for t in item["types"]:
        if t.get("id") == instance_type:
            return t.get("creditCost")

    return 1
