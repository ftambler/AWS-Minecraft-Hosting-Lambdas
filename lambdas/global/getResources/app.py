import boto3
import json
import os

# ENV: REGION, TABLE_NAME

def lambda_handler(event, context):
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["REGION"])
    table = dynamodb.Table(os.environ["TABLE_NAME"])

    try:
        response = table.get_item(Key={"PK": "GLOBAL", "SK": "RESOURCES"})
        item = response.get("Item", {})

        # Remove PK and SK
        item.pop("PK", None)
        item.pop("SK", None)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(item)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
