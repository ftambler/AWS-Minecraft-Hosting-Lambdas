import os
import boto3
import json
from botocore.exceptions import ClientError
from decimal import Decimal

#ENV: REGION, TABLE_NAME

dynamodb = boto3.resource("dynamodb", region_name=os.environ['REGION'])
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    query = event.get("queryStringParameters") or {}
    user_email = query.get("owner")

    if not user_email:
        return {"statusCode": 400, "body": "Missing 'owner' in request"}

    try:
        config = table.get_item(Key={"PK": f"USERS#{user_email}", "SK": "CONFIGPROFILE"})
        server = table.get_item(Key={"PK": f"USERS#{user_email}", "SK": "SERVER"})
        config_item = config.get("Item")
        server_item = server.get("Item")
    except ClientError as e:
        return {"statusCode": 500, "body": f"Error fetching item: {e}"}

    if not config_item or not server_item:
        return {"statusCode": 404, "body": "No server found for this user"}

    try:
        resources = table.get_item(Key={"PK": "GLOBAL", "SK": "RESOURCES"}).get("Item")
    except ClientError as e:
        return {"statusCode": 500, "body": f"Error fetching item: {e}"}

    config_item['Type'] = getResourceName(resources.get('types'), config_item['Type'])
    config_item['Region'] = getResourceName(resources.get('regions'), config_item['Region'])

    server_status = config_item | server_item
    server_status.pop('PK')
    server_status.pop('SK')

    return {"statusCode": 200, "body": json.dumps(server_status, default=str)}


def getResourceName(resources, id):
    for t in resources:
        if t.get("id") == id:
            return t.get("name")

    return id
