import boto3
import os
import json

#ENV: REGION, TABLE_NAME

dynamodb = boto3.resource("dynamodb", region_name=os.environ["REGION"])
table = dynamodb.Table(os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        if not body:
            return {"statusCode": 400, "body": "Empty body"}

        item = {
            "PK": "GLOBAL",
            "SK": "RESOURCES",
            "types": body.get("types", []),
            "versions": body.get("versions", []),
            "regions": body.get("regions", [])
        }

        table.put_item(Item=item)

        return {"statusCode": 200, "body": "Global resources created"}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    
# Example event

# {
#   "body": {
#       "types":[
#             {"id":"t2.small","name":"Chico (2–4 jugadores)"},
#             {"id":"t2.medium","name":"Mediano (5–10 jugadores)"},
#             {"id":"t2.large","name":"Grande (11–20 jugadores)"}
#         ],
#         "versions":[
#             {"id":"1.24","label":"1.24"},
#             {"id":"1.21.10","label":"1.21.10"},
#             {"id":"1.20","label":"1.20"}
#         ],
#         "regions":[
#             {"id":"us-east-1","name":"US NORTH"},
#             {"id":"sa-east-1","name":"SA EAST"},
#             {"id":"eu-west-1","name":"EU WEST"}
#         ]
#     }
# }