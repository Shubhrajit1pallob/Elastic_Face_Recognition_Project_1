import boto3
import os
import time

# Set these variables
INPUT_BUCKET_NAME = '0000000000-in-bucket'
SEND_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue'
RECEIVE_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue'
IMAGE_PATH = '/Users/shawn47/Documents/CSE 546 Cloud computing/Project1/face_images_1000/test_005.jpg'
IMAGE_KEY = os.path.basename(IMAGE_PATH)     # S3 key (filename)

print(IMAGE_KEY)

s3_client = boto3.client('s3', region_name='us-east-1')
sqs_client = boto3.client('sqs', region_name='us-east-1')

def s3_file_exists(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        print(f"Error checking S3 file existence: {e}")
        return False
    
def clear_sqs_queue(queue_url):
    while True:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=2
        )
        messages = response.get('Messages', [])
        if not messages:
            break
        for msg in messages:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=msg['ReceiptHandle']
            )
            
clear_sqs_queue(RECEIVE_QUEUE_URL)

# 1. Upload image to S3 input bucket

if not s3_file_exists(INPUT_BUCKET_NAME, IMAGE_KEY):
    print("Uploading image to S3...")
    s3_client.upload_file(IMAGE_PATH, INPUT_BUCKET_NAME, IMAGE_KEY)
    print(f"Uploaded {IMAGE_PATH} to s3://{INPUT_BUCKET_NAME}/{IMAGE_KEY}")
else:
    print(f"File {IMAGE_KEY} already exists in S3 bucket {INPUT_BUCKET_NAME}")

# 2. Send message to request SQS queue
print("Sending SQS request...")
sqs_client.send_message(
    QueueUrl=SEND_QUEUE_URL,
    MessageBody=IMAGE_KEY
)
print(f"Sent SQS message with image key: {IMAGE_KEY}")

# 3. Poll response SQS queue for result
print("Waiting for response from app tier...")
while True:
    response = sqs_client.receive_message(
        QueueUrl=RECEIVE_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5
    )
    messages = response.get('Messages', [])
    if messages:
        print("Received response:", messages[0]['Body'])
        # Delete the message from the queue
        sqs_client.delete_message(
            QueueUrl=RECEIVE_QUEUE_URL,
            ReceiptHandle=messages[0]['ReceiptHandle']
        )
        break
    else:
        print("No response yet, waiting...")
        time.sleep(2)