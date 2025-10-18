import boto3
import base64

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # Event Variables
    server_version = ""
    server_flags = "-Xmx1024M -Xms1024M"
    efs_id = ""                     #Conseguir esto en funcion de la region
    security_groups = []            #SG de la VPC (allow TCP 2049)
    subnet = ""                     #Subnet de la VPC

    #Lambda
    minecraft_jars = ""
    image_id = "ami-0c02fb55956c7d316"     #Amazon Linux AMI ID

    hasServer = False
    if(hasServer):
        serverUUID = ""                 #Conseguir de dinamo

        user_data = f'''#!/bin/bash
            sudo dnf install -y amazon-efs-utils
            sudo dnf install java-21-amazon-corretto -y
            
            sudo mkdir -p /mnt/efs
            sudo mount -t efs -o tls {efs_id}:/ /mnt/efs/{serverUUID}


            cd /mnt/efs/{serverUUID}
            java {server_flags} -jar server.jar nogui

            '''
    else:
        serverUUID = ""                 #Inventar algun UUID y subir al dynamo

        user_data = f'''#!/bin/bash
            sudo dnf install -y amazon-efs-utils
            sudo dnf install java-21-amazon-corretto -y
            
            sudo mkdir /mnt/efs
            sudo mount -t efs -o tls {efs_id}:/ /mnt/efs/{serverUUID}
                                                                         
            mkdir /mnt/efs/{serverUUID}
            cd /mnt/efs/{serverUUID}
            
            aws s3 cp s3://{minecraft_jars}/{server_version}/server.jar .
            echo "eula=true" > eula.txt
            chown (ver bien esto)

            java {server_flags} -jar server.jar nogui

            '''
        
    # Define EC2 instance parameters
    instance_params = {
        'ImageId': image_id,
        'InstanceType': event['server-type'],
        'MinCount': 1,
        'MaxCount': 1,
        'SecurityGroupIds': security_groups,
        'SubnetId': subnet,
        'UserData': user_data
    }

    try:
        response = ec2.run_instances(**instance_params)
        instance_id = response['Instances'][0]['InstanceId']

        # Get Public IP
        ec2_resource = boto3.resource('ec2')
        instance = ec2_resource.Instance(instance_id)
        instance.wait_until_running()
        instance.load()
        public_ip = instance.public_ip_address

        return {
            'statusCode': 200,
            'body': {
                'instance_id': instance_id,
                'public_ip': public_ip,
            }
        }
    except Exception as e:
        print(f"Error launching EC2 instance: {e}")
        return {
            'statusCode': 500,
            'body': f'Error launching EC2 instance: {e}'
        }