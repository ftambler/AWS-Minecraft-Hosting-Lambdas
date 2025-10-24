import os
import json
import boto3

lambda_client = boto3.client("lambda")

# Map operation names to target Lambda function names
ROUTE_MAP = {
    "CREATE": "createServer",
    "DELETE": "deleteServer",
    # "LIST_SERVERS": "listServers"
}

def lambda_handler(event, context):
    # If triggered by SQS, messages come in event['Records']
    messages = event.get("Records", [event])
    results = []

    for record in messages:
        body = record.get("body", record)
        if isinstance(body, str):
            body = json.loads(body)

        operation = body.get("operation")
        payload = body.get("payload", {})

        if operation not in ROUTE_MAP:
            print(f"Unknown operation: {operation}")
            continue

        target_lambda = ROUTE_MAP[operation]
        print(f"Routing to: {target_lambda}")

        response = lambda_client.invoke(
            FunctionName=target_lambda,
            InvocationType="Event",  # async call (use 'RequestResponse' if you want to wait)
            Payload=json.dumps(payload)
        )

        results.append({
            "operation": operation,
            "target": target_lambda,
            "status": response["StatusCode"]
        })

    return {"results": results}
