import boto3
import json

def lambda_handler(event, context):
    operation = event['operation']

    sqs = boto3.client('sqs')
    queue_url = "SQS_URL"
    message_body = {}

    match operation:
        case 'CREATE':
            message_body = {
                'operation': 'CREATE',
                'type': event['server-type'],
                'version': event['server-version'],
                'region': event['server-region'],
                'owner': event['ownerUUID']
            }
        case 'DELETE': 
            message_body = {
                'operation': 'DELETE',
                'owner': event['ownerUUID']
            } 
        case 'TURNOFF': 
            message_body = {
                'operation': 'TURNOFF',
                'owner': event['ownerUUID']
            }
        case 'TURNON': 
            message_body = {
                'operation': 'TURNON',
                'owner': event['ownerUUID']
            }


    try:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
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