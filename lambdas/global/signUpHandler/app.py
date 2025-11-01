import os
import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ['REGION'])
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    print(f"Received {event}")
    if event['triggerSource'] == 'PostConfirmation_ConfirmSignUp':
        user_email = event['request']['userAttributes'].get('email')
        user_name = event.get('name', 'notfound')

        table.put_item(Item= { "PK": f"USERS#{user_email}", "SK": "PROFILE", "Name": user_name, "Credits": 0 })

    return event