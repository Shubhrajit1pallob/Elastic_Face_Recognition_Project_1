import boto3
import os

INPUT_BUCKET_NAME = '0000000000-in-bucket'
OUTPUT_BUCKET_NAME = '0000000000-out-bucket'
SEND_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue'
RECEIVE_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue'
IMAGE_DIR = '/Users/shawn47/Documents/CSE 546 Cloud computing/Project1/face_images_1000'

s3_client = boto3.client('s3', region_name='us-east-1')
sqs_client = boto3.client('sqs', region_name='us-east-1')

def clear_bucket(bucket_name):
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        objects = [{'Key': obj['Key']} for obj in response['Contents']]
        print(f"Deleting {len(objects)} objects from {bucket_name}...")
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={'Objects': objects}
        )

def s3_file_exists(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False

def send_batch_requests(num_files=50):
    files = [f"test_{i:03d}.jpg" for i in range(num_files)]

    for fname in files:
        image_path = os.path.join(IMAGE_DIR, fname)
        image_key = fname

        # Upload to S3 if not already present
        if not s3_file_exists(INPUT_BUCKET_NAME, image_key):
            print(f"Uploading {image_key} to S3...")
            s3_client.upload_file(image_path, INPUT_BUCKET_NAME, image_key)
        else:
            print(f"{image_key} already exists in S3.")

        # Send SQS request
        sqs_client.send_message(
            QueueUrl=SEND_QUEUE_URL,
            MessageBody=image_key
        )
        print(f"Sent SQS message for {image_key}")
        
def receive_responses():
    
    while True:
        response = sqs_client.receive_message(
            QueueUrl=RECEIVE_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5
        )
        if 'Messages' not in response:
            break
        messages = response.get('Messages', [])
        for msg in messages:
            print(f"Received response: {msg['Body']}")
            sqs_client.delete_message(
                QueueUrl=RECEIVE_QUEUE_URL,
                ReceiptHandle=msg['ReceiptHandle']
            )

def clear_queue(queue_url):
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

if __name__ == "__main__":
    clear_bucket(INPUT_BUCKET_NAME)
    clear_bucket(OUTPUT_BUCKET_NAME)
    # if len(sqs_client.list_queues().get('QueueUrls', [])) > 0:
    #     clear_queue(SEND_QUEUE_URL)
    #     clear_queue(RECEIVE_QUEUE_URL)
    # send_batch_requests(num_files=300)
    # receive_responses()