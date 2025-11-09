import json
import boto3

def lambda_handler(event, context):
    messages = event.get("Records", [event])
    results = []

    for record in messages:
        body = record.get("body", record)
        if isinstance(body, str):
            body = json.loads(body)

        operation = body.get("operation")
        payload = body.get("payload", {})
        region = payload.get("region", "us-east-1")

        # Construct name dynamically
        function_base = {
            "CREATE": "createServer",
            "DELETE": "deleteServer",
            "TURNON": "turnOnServer",
            "TURNOFF": "turnOffServer"
        }.get(operation)

        if not function_base:
            print(f"Unknown operation: {operation}")
            continue

        function_name = f"{function_base}-{region}"
        print(f"Routing {operation} with body {payload} to {function_name} in {region}")

        lambda_client = boto3.client("lambda", region_name=region)
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps(payload)
        )

        results.append({
            "operation": operation,
            "region": region,
            "target": function_name,
            "status": response["StatusCode"]
        })

    return {"results": results}
