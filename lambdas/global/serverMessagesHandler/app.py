import boto3
import json
import os

#ENV: QUEUE_URL

sqs = boto3.client('sqs')

def lambda_handler(event, context):    
    body_raw = event.get("body", "{}")
    
    try:
        body = json.loads(body_raw)
    except json.JSONDecodeError:
        body = {}

    operation = body.get('operation')

    if not operation:
        return {'statusCode': 400, 'body': json.dumps('Missing operation field')}

    required_keys = {
        'CREATE': ['serverType', 'serverVersion', 'serverRegion', 'owner', 'serverName'],
        'DELETE': ['owner'],
        'TURNON': ['owner'],
        'TURNOFF': ['owner']
    }

    # Check all required fields are in the message
    for key in required_keys.get(operation, []):
        if key not in body:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Missing required parameter: {key}")
            }

    #Build message
    match operation:
        case 'CREATE':
            message_body = {
                'operation': 'CREATE',
                'payload': {
                    'type': body['serverType'],
                    'version': body['serverVersion'],
                    'region': body['serverRegion'],
                    'owner': body['owner'],
                    'serverName': body['serverName']
                }
            }
        case 'DELETE' | 'TURNON' | 'TURNOFF':
            message_body = {
                'operation': operation,
                'payload': {
                    'owner': body['owner']
                }                
            }
        case _:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Unsupported operation: {operation}")
            }

    try:
        sqs.send_message(
            QueueUrl=os.environ['QUEUE_URL'],
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'Operation': {'DataType': 'String', 'StringValue': operation},
                'Owner': {'DataType': 'String', 'StringValue': body['owner']}
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps('Message sent successfully!')
        }
    except Exception as e:
        print(f'Error sending message to SQS: {e}')
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error sending message: {str(e)}')
        }
