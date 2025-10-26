# import time
# from face_recognition import face_match
# import boto3
# import os

# # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# # MODEL_PATH = os.path.join(SCRIPT_DIR, 'data.pt')

# def load_env_var(var_name, default=None, env_file='/etc/app-tier.env'):
#     with open(env_file) as f:
#         for line in f:
#             if line.startswith(var_name + '='):
#                 return line.strip().split('=', 1)[1]
#     return default

# RECEIVE_QUEUE_URL = load_env_var('RECEIVE_QUEUE_URL', default='https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue')
# SEND_QUEUE_URL = load_env_var('SEND_QUEUE_URL', default='https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue')
# INPUT_BUCKET_NAME = load_env_var('INPUT_BUCKET_NAME', default='0000000000-in-bucket')
# OUTPUT_BUCKET_NAME = load_env_var('OUTPUT_BUCKET_NAME', default='0000000000-out-bucket')
# DOWNLOAD_PATH = load_env_var('DOWNLOAD_PATH', default='/tmp/images/')

# os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# sqs_client = boto3.client('sqs', region_name='us-east-1')
# s3_client = boto3.client('s3', region_name='us-east-1')

# def sqs_receive_message():
#     response = sqs_client.receive_message(
#         QueueUrl=RECEIVE_QUEUE_URL,
#         MaxNumberOfMessages=1,
#         WaitTimeSeconds=10
#     )
#     messages = response.get('Messages', [])
#     if messages:
#         return messages[0]
#     return None

# def sqs_send_message(body):
#     try:
#         print(f"Attempting to send message: {body}")
#         response = sqs_client.send_message(
#             QueueUrl=SEND_QUEUE_URL,  # Make sure this is the RESPONSE queue URL
#             MessageBody=body,
#             MessageAttributes={
#                 'timestamp': {
#                     'StringValue': str(time.time()),
#                     'DataType': 'String'
#                 }
#             }
#         )
#         print(f"Successfully sent message with ID: {response['MessageId']}")
#         return response['MessageId']
#     except Exception as e:
#         print(f"Error sending message to SQS: {e}")
#         raise

# def get_image_from_s3(bucket, key, download_path):
#     s3_client.download_file(bucket, key, download_path)

# def put_image_to_s3(bucket, key, result):
#     s3_client.put_object(Bucket=bucket, Key=key, Body=result)

# def process_image(key):
#     if key is not None:
#         local_path = os.path.join(DOWNLOAD_PATH, os.path.basename(key['Body']))
#         get_image_from_s3(INPUT_BUCKET_NAME, key['Body'], local_path)
#         name, distance = face_match(local_path, data_path='data.pt')
#         return name, distance

#     return None, None

# if __name__ == "__main__":
#     print("Starting backend service...")
#     while True:
#         try:
#             key = sqs_receive_message()
#             if key is not None and 'Body' in key:
#                 sqs_client.delete_message(
#                     QueueUrl=RECEIVE_QUEUE_URL,
#                     ReceiptHandle=key['ReceiptHandle']
#                 )
#                 result = process_image(key)
#                 if result is not None:
#                     name, distance = result
#                     output_key = os.path.splitext(os.path.basename(key['Body']))[0]
#                     result = f"{output_key}:{name}"
#                     message_id = sqs_send_message(result)
#                     put_image_to_s3(OUTPUT_BUCKET_NAME, output_key, name)
#                     # print(f"Processed image. Identified: {name} with distance {distance}. Message ID: {message_id}")
#                     print(f"Result name: {result} and Output Key: {output_key}")
#                 else:
#                     print("No image processed.")
#             else:
#                 print("No message in queue, waiting...")
#         except Exception as e:
#             print(f"Error processing message: {e}")
#             continue
    
    
import time
from face_recognition import face_match
import boto3
import os

def load_env_var(var_name, default=None, env_file='/etc/app-tier.env'):
    with open(env_file) as f:
        for line in f:
            if line.startswith(var_name + '='):
                return line.strip().split('=', 1)[1]
    return default

RECEIVE_QUEUE_URL = load_env_var('RECEIVE_QUEUE_URL', default='https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue')
SEND_QUEUE_URL = load_env_var('SEND_QUEUE_URL', default='https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue')
INPUT_BUCKET_NAME = load_env_var('INPUT_BUCKET_NAME', default='0000000000-in-bucket')
OUTPUT_BUCKET_NAME = load_env_var('OUTPUT_BUCKET_NAME', default='0000000000-out-bucket')
DOWNLOAD_PATH = load_env_var('DOWNLOAD_PATH', default='/tmp/images/')

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

sqs_client = boto3.client('sqs', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')

def sqs_receive_message():
    response = sqs_client.receive_message(
        QueueUrl=RECEIVE_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
        VisibilityTimeout=60  # Give enough time to process
    )
    messages = response.get('Messages', [])
    if messages:
        return messages[0]
    return None

def sqs_send_message(body):
    try:
        print(f"Sending message to response queue: {body}")
        response = sqs_client.send_message(
            QueueUrl=SEND_QUEUE_URL,
            MessageBody=body
        )
        print(f"Message sent successfully. ID: {response['MessageId']}")
        return response['MessageId']
    except Exception as e:
        print(f"Error sending message to SQS: {e}")
        raise

def get_image_from_s3(bucket, key, download_path):
    s3_client.download_file(bucket, key, download_path)

def put_image_to_s3(bucket, key, result):
    s3_client.put_object(Bucket=bucket, Key=key, Body=result)

def process_message(message_body):
    """Parse message and extract request_id and filename"""
    # Handle both formats: "request_id|filename" or just "filename"
    if '|' in message_body:
        request_id, filename = message_body.split('|', 1)
        return request_id, filename
    else:
        return None, message_body

if __name__ == "__main__":
    print("Starting backend service...")
    print(f"Receiving from: {RECEIVE_QUEUE_URL}")
    print(f"Sending to: {SEND_QUEUE_URL}")
    
    while True:
        try:
            message = sqs_receive_message()
            
            if message is not None and 'Body' in message:
                print(f"Received message: {message['Body']}")
                
                # Parse message
                request_id, filename = process_message(message['Body'])
                
                # Download and process image
                local_path = os.path.join(DOWNLOAD_PATH, os.path.basename(filename))
                get_image_from_s3(INPUT_BUCKET_NAME, filename, local_path)
                
                name, distance = face_match(local_path, data_path='data.pt')
                
                # Create output key (without extension)
                output_key = os.path.splitext(os.path.basename(filename))[0]
                
                # Format response based on whether we have request_id
                if request_id:
                    response_body = f"{output_key}:{request_id}:{name}"
                else:
                    response_body = f"{output_key}:{name}"
                
                print(f"Recognition result: {name} (distance: {distance})")
                
                # Send response
                message_id = sqs_send_message(response_body)
                
                # Store result in S3
                put_image_to_s3(OUTPUT_BUCKET_NAME, output_key, name)
                
                # Delete message from request queue
                sqs_client.delete_message(
                    QueueUrl=RECEIVE_QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                
                print(f"Completed processing. Response: {response_body}")
                
            else:
                print("No message in queue, waiting...")
                
        except Exception as e:
            print(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)