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
    AMI_ID = os.getenv('AMI_ID', 'ami-048b292d89c02281d')
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
    idle_cycles = 0
    IDLE_THRESHOLD = 3
    
    while True:
        try:
            queue_len = get_queue_length(queue_url)
            print(f"\nQueue length: {queue_len}")
            
            # Get instance counts
            running = get_app_instances('running')
            pending = get_app_instances('pending')
            stopped = get_app_instances('stopped')
            
            active_count = len(running) + len(pending)
            print(f"Running: {len(running)}, Pending: {len(pending)}, Stopped: {len(stopped)}")
            
            # Scale UP: Queue has work
            if queue_len > 0:
                idle_cycles = 0
                desired = min(queue_len, MAX_INSTANCES)
                needed = desired - active_count
                
                if needed > 0:
                    print(f"Need {needed} more instances")
                    
                    # Prioritize restarting stopped instances
                    to_restart = min(len(stopped), needed)
                    for i in range(to_restart):
                        instance_id = stopped[i]['InstanceId']
                        print(f"Restarting stopped instance: {instance_id}")
                        start_instance(instance_id)
                        needed -= 1
                    
                    # Launch new instances if still needed
                    for _ in range(needed):
                        instance_id = launch_app_tier()
                        print(f"Launched new instance: {instance_id}")
            
            # Scale DOWN: Queue empty
            elif active_count > 0:
                idle_cycles += 1
                print(f"Idle cycles: {idle_cycles}/{IDLE_THRESHOLD}")
                
                if idle_cycles >= IDLE_THRESHOLD:
                    print("Stopping all running instances")
                    for instance in running:
                        print(f"Stopping: {instance['InstanceId']}")
                        stop_instance(instance['InstanceId'])
                    idle_cycles = 0
            
            time.sleep(10)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    print("Starting controller service...")
    print(f"Instances running at start: {len(get_app_instances('running'))}")
    scale(SEND_QUEUE_URL)