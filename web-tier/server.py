from flask import Flask, request, jsonify
import os
import boto3
import csv
import time
import uuid

app = Flask(__name__)


# Initialize the s3 client
s3_client = boto3.client('s3', region_name='us-east-1')
BUCKET_NAME = '0000000000-in-bucket'

INPUT_BUCKET_NAME = os.getenv('INPUT_BUCKET_NAME','0000000000-in-bucket')
OUTPUT_BUCKET_NAME = os.getenv('OUTPUT_BUCKET_NAME','0000000000-out-bucket')

sqs_client = boto3.client('sqs', region_name='us-east-1')
SEND_QUEUE_URL = os.getenv('SEND_QUEUE_URL','https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue')
RECEIVE_QUEUE_URL = os.getenv('RECEIVE_QUEUE_URL','https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue')

# def delete_domain():
#     try:
#         sdb_client.delete_domain(DomainName=DOMAIN_NAME)
#         print(f"Deleted domain: {DOMAIN_NAME}")
#         return True
#     except Exception as e:
#         print(f"Error deleting domain: {e}")
#         return False



# @app.route("/", methods=['POST'])
# def handle_request():
#     if 'inputFile' not in request.files:
#         return jsonify({"error": "No file part in the request"}), 400  
    
#     file = request.files['inputFile']
#     filename = file.filename
#     print(f"Received file: {filename}")
    
#     try:
#         # Upload to S3
#         s3_client.upload_fileobj(file, INPUT_BUCKET_NAME, filename)
#         print(f"Uploaded file to S3: {filename}")

#         # Send to request queue
#         sqs_client.send_message(
#             QueueUrl=SEND_QUEUE_URL,
#             MessageBody=filename
#         )
#         print(f"Sent to request queue: {filename}")

#         if not filename:
#             return jsonify({"error": "Filename is None"}), 400

#         # Wait for response
#         expected_prefix = filename.rsplit('.', 1)[0] + ':'
#         print(f"Waiting for response with prefix: {expected_prefix}")
        
#         timeout = 120  # Increase timeout to 120 seconds
#         start_time = time.time()
        
#         while time.time() - start_time < timeout:
#             try:
#                 response = sqs_client.receive_message(
#                     QueueUrl=RECEIVE_QUEUE_URL,
#                     MaxNumberOfMessages=10,
#                     WaitTimeSeconds=2
#                 )
                
#                 messages = response.get('Messages', [])
#                 if messages:
#                     print(f"Checking {len(messages)} messages")
                    
#                     for msg in messages:
#                         print(f"Checking message: {msg['Body']}")
#                         if msg['Body'].startswith(expected_prefix):
#                             # Found our response
#                             print(f"Found matching response: {msg['Body']}")
#                             sqs_client.delete_message(
#                                 QueueUrl=RECEIVE_QUEUE_URL,
#                                 ReceiptHandle=msg['ReceiptHandle']
#                             )
#                             return msg['Body'], 200, {'Content-Type': 'text/plain'}
#                         else:
#                             # Make non-matching messages visible again
#                             try:
#                                 sqs_client.change_message_visibility(
#                                     QueueUrl=RECEIVE_QUEUE_URL,
#                                     ReceiptHandle=msg['ReceiptHandle'],
#                                     VisibilityTimeout=0
#                                 )
#                             except Exception as e:
#                                 print(f"Error changing visibility: {e}")
                
#                 time.sleep(1)
#             except Exception as e:
#                 print(f"Error receiving messages: {e}")
#                 time.sleep(1)
#                 continue

#         print(f"Timeout waiting for: {filename}")
#         return "Timeout waiting for result", 504, {'Content-Type': 'text/plain'}
        
#     except Exception as e:
#         print(f"Error processing request: {e}")
#         return str(e), 500, {'Content-Type': 'text/plain'}



@app.route("/", methods=['POST'])
def handle_request():
    if 'inputFile' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400  
    
    file = request.files['inputFile']
    filename = file.filename
    
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
        
    print(f"Received file: {filename}")
    
    try:
        # Upload to S3
        s3_client.upload_fileobj(file, INPUT_BUCKET_NAME, filename)
        print(f"Uploaded to S3: {filename}")

        # Generate unique request ID
        request_id = str(uuid.uuid4())
        message_body = f"{request_id}|{filename}"
        
        # Send to request queue
        sqs_client.send_message(
            QueueUrl=SEND_QUEUE_URL,
            MessageBody=message_body
        )
        print(f"Sent to queue: {message_body}")

        # Wait for response
        expected_prefix = f"{filename.rsplit('.', 1)[0]}:{request_id}:"
        print(f"Waiting for: {expected_prefix}")
        
        timeout = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = sqs_client.receive_message(
                    QueueUrl=RECEIVE_QUEUE_URL,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=5,
                    VisibilityTimeout=30
                )
                
                messages = response.get('Messages', [])
                if not messages:
                    continue
                    
                print(f"Checking {len(messages)} messages")
                
                for msg in messages:
                    msg_body = msg['Body']
                    receipt_handle = msg['ReceiptHandle']
                    
                    if msg_body.startswith(expected_prefix):
                        # msg_body format: "test1:uuid-123:Alice"
                        # We need to return: "test1:Alice"
                        parts = msg_body.split(':', 2)
                        if len(parts) >= 3:
                            # parts[0] = "test1", parts[1] = "uuid-123", parts[2] = "Alice"
                            result = f"{parts[0]}:{parts[2]}"  # "test1:Alice"
                        else:
                            # Fallback for old format without request_id
                            result = msg_body
                        
                        print(f"Returning result: '{result}'")
                        
                        sqs_client.delete_message(
                            QueueUrl=RECEIVE_QUEUE_URL,
                            ReceiptHandle=receipt_handle
                        )
                        return result, 200, {'Content-Type': 'text/plain'}
                    else:
                        # Not our message - return to queue
                        try:
                            sqs_client.change_message_visibility(
                                QueueUrl=RECEIVE_QUEUE_URL,
                                ReceiptHandle=receipt_handle,
                                VisibilityTimeout=0
                            )
                        except Exception as e:
                            print(f"Error returning message to queue: {e}")
                            
            except Exception as e:
                print(f"Error polling queue: {e}")
                time.sleep(1)

        print(f"Timeout after {timeout}s waiting for: {filename}")
        return "Request timeout", 504, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return str(e), 500, {'Content-Type': 'text/plain'}
        

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0', threaded=True)