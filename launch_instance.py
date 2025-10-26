import boto3
import time

def get_instance_status(ec2_client, instance_id):
    response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
    if response['InstanceStatuses']:
        return response['InstanceStatuses'][0]['InstanceStatus']['Status']
    return "Not available"

def check_system_logs(instance_id):
    ssm_client = boto3.client('ssm', region_name='us-east-1')
    try:
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': ['journalctl -u app-tier.service -n 50']}
        )
        command_id = response['Command']['CommandId']
        time.sleep(5)  # Wait for logs to be available
        
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        return output.get('StandardOutputContent', '')
    except Exception as e:
        print(f"Could not get logs: {e}")
        return None

def launch_app_tier():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Replace with your AMI ID from the Packer build
    AMI_ID = 'ami-0b8c0ec51630182db'
    KEY_NAME = 'Shubhrajit-EC2-Keypair'
    SG_ID = 'sg-048a60be48ffbffc7'
    SUBNET_ID = 'subnet-09d62497e682d7e3e'
    IAM_PROFILE = 'app-tier-profile'

    print(f"Launching new instance from AMI {AMI_ID}...")
    response = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        KeyName=KEY_NAME,
        NetworkInterfaces=[{
            'SubnetId': SUBNET_ID,
            'Groups': [SG_ID],
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True
        }],
        IamInstanceProfile={'Name': IAM_PROFILE},
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'app-tier-instance-1'}]
        }]
    )
    
    instance_id = response['Instances'][0]['InstanceId']
    print(f"Launched instance: {instance_id}")
    
    # Wait for instance to be running
    print("Waiting for instance to be ready...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print("Instance is running!")
    
    # Add status checks
    while True:
        print("\nChecking instance status...")
        status = get_instance_status(ec2, instance_id)
        if status != 'initializing':
            print(f"Instance status: {status}")
            break
        print(f"Status: {status}. Retrying in 10 seconds...")
        time.sleep(10)
    
    # print("\nChecking instance status...")
    # status = get_instance_status(ec2, instance_id)
    # print(f"Instance status: {status}")
    
    # # Wait for system initialization
    # print("\nWaiting 60 seconds for system initialization...")
    # time.sleep(60)
    
    # Check service logs
    print("\nChecking app-tier service logs...")
    logs = check_system_logs(instance_id)
    if logs:
        print("Recent logs from app-tier service:")
        print(logs)
    else:
        print("Could not retrieve logs. Please check EC2 instance directly.")
        
    
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = desc['Reservations'][0]['Instances'][0].get('PublicIpAddress')
    print(f"Public IP: {public_ip}")
    print(f"SSH command: ssh -i /path/to/Shubhrajit-EC2-Keypair.pem ubuntu@{public_ip}")
    
    return instance_id

if __name__ == "__main__":
    instance_id = launch_app_tier()
    print("\nInstance is ready for testing!")
    print(f"Instance ID: {instance_id}")
    print("You can now run backend_test.py to process images.")