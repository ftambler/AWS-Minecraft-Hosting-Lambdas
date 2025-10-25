import boto3
import json
import os

def lambda_handler(event, context):    
    sqs = boto3.client('sqs')
    
    sqs_url = os.getenv('QUEUE_URL')
    operation = event.get('operation')

    if not operation:
        return {'statusCode': 400, 'body': json.dumps('Missing operation field')}

    required_keys = {
        'CREATE': ['server-type', 'server-version', 'server-region', 'owner'],
        'DELETE': ['owner'],
        'TURNON': ['owner'],
        'TURNOFF': ['owner']
    }

    # Check all required fields are in the message
    for key in required_keys.get(operation, []):
        if key not in event:
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
                    'type': event['server-type'],
                    'version': event['server-version'],
                    'region': event['server-region'],
                    'owner': event['owner']
                }
            }
        case 'DELETE' | 'TURNON' | 'TURNOFF':
            message_body = {
                'operation': operation,
                'owner': event['owner']
            }
        case _:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Unsupported operation: {operation}")
            }

    try:
        sqs.send_message(
            QueueUrl=sqs_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'Operation': {'DataType': 'String', 'StringValue': operation},
                'Owner': {'DataType': 'String', 'StringValue': event['owner']}
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
