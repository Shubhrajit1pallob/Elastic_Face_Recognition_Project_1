import boto3
import time
import os

ec2 = boto3.client('ec2', region_name='us-east-1')
sqs = boto3.client('sqs', region_name='us-east-1')

TAG_KEYS = 'Name'
# TAG_VALUES = 'app-tier-instance'
SEND_QUEUE_URL = os.getenv('SEND_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue')
MAX_INSTANCES = 15
COUNT = 0

def get_queue_length(queue_url):
    attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )['Attributes']
    return int(attributes['ApproximateNumberOfMessages'])

def get_app_instances(type):
    
    instances = []
    
    if type == 'running':
        
        resp = ec2.describe_instances(
            Filters=[
                {
                    'Name': f'tag:{TAG_KEYS}',
                    'Values': ['app-tier-instance']
                },
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)
                
    elif type == 'stopped':
        resp = ec2.describe_instances(
            Filters=[
                {'Name': f'tag:{TAG_KEYS}', 'Values': ['app-tier-instance']},
                {'Name': 'instance-state-name', 'Values': ['stopped']}
            ]
        )
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)   
    
    elif type == 'pending':
        resp = ec2.describe_instances(
            Filters=[
                {'Name': f'tag:{TAG_KEYS}', 'Values': ['app-tier-instance']},
                {'Name': 'instance-state-name', 'Values': ['pending']}
            ]
        )
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)
                
    elif type == 'all':
        resp = ec2.describe_instances(
            Filters=[
                {'Name': f'tag:{TAG_KEYS}', 'Values': ['app-tier-instance']}
            ]
        )
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)
    
    elif type == 'active':
        # Active = running + pending (instances that are or will be available)
        resp = ec2.describe_instances(
            Filters=[
                {'Name': f'tag:{TAG_KEYS}', 'Values': ['app-tier-instance']},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)
                
    elif type == 'terminated':
        resp = ec2.describe_instances(
            Filters=[
                {'Name': f'tag:{TAG_KEYS}', 'Values': ['app-tier-instance']},
                {'Name': 'instance-state-name', 'Values': ['terminated']}
            ]
        )
        
        for reservation in resp['Reservations']:
            for inst in reservation['Instances']:
                instances.append(inst)
                    

    return instances


def start_instance(instance_id):
    ec2.start_instances(InstanceIds=[instance_id])
    
def stop_instance(instance_id):
    ec2.stop_instances(InstanceIds=[instance_id])

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
    global COUNT
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Replace with your AMI ID from the Packer build
    AMI_ID = os.getenv('AMI_ID', 'ami-0172bcd94efa5ae95')
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
            'Tags': [{'Key': 'Name', 'Value': f'app-tier-instance'}]
        }]
    )

    instance_id = response['Instances'][0]['InstanceId']
    print(f"Launched instance: {instance_id}")
    
    
    return instance_id
    

        
def scale(queue_url):
    print("Starting scaling loop...")
    idle_cycles = 0  # Track how many cycles the queue has been empty
    IDLE_THRESHOLD = 3  # Number of idle cycles before scaling down
    
    while True:
        queue_len = get_queue_length(queue_url)
        print(f"Current queue length: {queue_len}")
        
        running = get_app_instances('running')
        print(f"Currently running instances: {len(running)}")
        
        pending = get_app_instances('pending')
        print(f"Currently pending instances: {len(pending)}")
        
        stopped = get_app_instances('stopped')
        print(f"Currently stopped instances: {len(stopped)}")
        
        # Active instances = running + pending
        active_count = len(running) + len(pending)
        print(f"Active instances (running + pending): {active_count}")
        
        # Total capacity = active + stopped (excludes terminated)
        total_capacity = active_count + len(stopped)
        print(f"Total capacity: {total_capacity}")

        # Scale UP logic
        if queue_len > 0:
            idle_cycles = 0  # Reset idle counter
            
            # Calculate how many instances we need total
            desired_instances = min(queue_len, MAX_INSTANCES)
            instances_needed = desired_instances - active_count
            
            print(f"Desired instances: {desired_instances}, Need to add: {instances_needed}")
            
            if instances_needed > 0 and active_count < MAX_INSTANCES:
                # First, start stopped instances
                if stopped:
                    num_to_start = min(instances_needed, len(stopped))
                    print(f"Starting {num_to_start} stopped instance(s)...")
                    for i in stopped[:num_to_start]:
                        print(f"Starting stopped instance: {i['InstanceId']}")
                        start_instance(i['InstanceId'])
                        instances_needed -= 1
                
                # Then, launch new instances if still needed
                if instances_needed > 0 and total_capacity < MAX_INSTANCES:
                    num_to_launch = min(instances_needed, MAX_INSTANCES - total_capacity)
                    print(f"Launching {num_to_launch} new instance(s)...")
                    for _ in range(num_to_launch):
                        launch_app_tier()
        
        # Scale DOWN logic (with grace period)
        elif queue_len == 0:
            idle_cycles += 1
            print(f"Queue empty. Idle cycles: {idle_cycles}/{IDLE_THRESHOLD}")
            
            if idle_cycles >= IDLE_THRESHOLD and running:
                print(f"Scaling down after {idle_cycles} idle cycles...")
                for i in running:
                    print(f"Stopping running instance: {i['InstanceId']}")
                    stop_instance(i['InstanceId'])
                idle_cycles = 0  # Reset after scaling down
        
        # Otherwise, sleep before next check
        print("Sleeping for 10 seconds before next check...")
        time.sleep(10)

if __name__ == "__main__":
    print("Starting controller service...")
    print(f"Instances running at start: {len(get_app_instances('running'))}")
    scale(SEND_QUEUE_URL)