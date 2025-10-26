from flask import Flask, request, jsonify
import os
import boto3
import csv
import time

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



@app.route("/", methods=['POST'])
def handle_request():
    if 'inputFile' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400  
    
    file = request.files['inputFile']
    filename = file.filename
    print(f"Received file: {filename}")
    
    try:
        s3_client.upload_fileobj(file, INPUT_BUCKET_NAME, filename)
        print(f"Uploaded file to S3 bucket {INPUT_BUCKET_NAME} with key {filename}")

        # Send the filename as message to SQS
        sqs_client.send_message(
            QueueUrl=SEND_QUEUE_URL,
            MessageBody=filename
        )

        if not filename:
            return jsonify({"error": "Filename is None, cannot process request."}), 400

        expected_prefix = filename.rsplit('.', 1)[0] + ':'
        timeout = 60  # seconds
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = sqs_client.receive_message(
                QueueUrl=RECEIVE_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=2
            )
            messages = response.get('Messages', [])
            for msg in messages:
                if msg['Body'].startswith(expected_prefix):
                    sqs_client.delete_message(
                        QueueUrl=RECEIVE_QUEUE_URL,
                        ReceiptHandle=msg['ReceiptHandle']
                    )
                    return msg['Body'], 200, {'Content-Type': 'text/plain'}
            time.sleep(1)
        # Timeout
        return "Timeout waiting for result", 504, {'Content-Type': 'text/plain'}
    except Exception as e:
        return str(e), 500, {'Content-Type': 'text/plain'}
        

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0', threaded=True)