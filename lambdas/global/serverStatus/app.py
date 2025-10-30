import os
import boto3
import json
from botocore.exceptions import ClientError
from decimal import Decimal

# ENV: REGION, TABLE_NAME

def lambda_handler(event, context):
    user_email = event.get("owner")

    if not user_email:
        return {"statusCode": 400, "body": "Missing 'owner' in request"}

    dynamodb = boto3.resource("dynamodb", region_name=os.environ['REGION'])
    table = dynamodb.Table(os.environ["TABLE_NAME"])

    try:
        response = table.get_item(Key={"PK": f"USERS#{user_email}", "SK": "SERVER"})
        item = response.get("Item")
    except ClientError as e:
        return {"statusCode": 500, "body": f"Error fetching item: {e}"}

    if not item:
        return {"statusCode": 404, "body": "No server found for this user"}

    def clean(obj):
        if isinstance(obj, list):
            return [clean(i) for i in obj]
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    item = clean(item)
    return {"statusCode": 200, "body": json.dumps(item)}
