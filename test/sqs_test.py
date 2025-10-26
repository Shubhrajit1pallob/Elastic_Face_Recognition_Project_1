import time
import boto3

# Replace with your actual queue URL
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue'
QUEUE_URL1 = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue'

sqs = boto3.client('sqs', region_name='us-east-1')

def send_message(body):
    response = sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=body)
    print("Sent message ID:", response['MessageId'])
    return response['MessageId']

def receive_message():
    response = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=2)
    messages = response.get('Messages', [])
    if messages:
        print("Received message:", messages[0]['Body'])
        receipt_handle = messages[0]['ReceiptHandle']
        return messages[0]['Body'], receipt_handle
    else:
        print("No messages received.")
        return None, None

def delete_message(receipt_handle):
    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
    print("Deleted message.")

def purge_queue(queue_url):
    print(f"Purging queue: {queue_url}")
    
    # First, try to purge the queue (removes all messages)
    try:
        sqs.purge_queue(QueueUrl=queue_url)
        print("Queue purged via purge_queue API")
        time.sleep(60)  # Wait for purge to complete (AWS requirement)
    except Exception as e:
        print(f"Purge failed: {e}")
    
    # Then handle any in-flight messages
    max_attempts = 5  # Maximum number of attempts to check for messages
    attempts = 0
    
    while attempts < max_attempts:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=0,  # Don't wait for new messages
            VisibilityTimeout=1
        )
        
        messages = response.get('Messages', [])
        if not messages:
            print(f"No messages found (attempt {attempts + 1}/{max_attempts})")
            attempts += 1
            continue
            
        for msg in messages:
            try:
                sqs.change_message_visibility(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg['ReceiptHandle'],
                    VisibilityTimeout=0
                )
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg['ReceiptHandle']
                )
                print(f"Deleted message: {msg['Body']}")
                attempts = 0  # Reset attempts if we found messages
            except Exception as e:
                print(f"Failed to delete message: {e}")
    
    print(f"Finished purging queue {queue_url}")
    
if __name__ == "__main__":
    # Test sending
    # send_message("Hello SQS!")

    # Test receiving
    # body, handle = receive_message()

    # # Test deleting
    # if handle:
    #     delete_message(handle)

    purge_queue(QUEUE_URL)
    purge_queue(QUEUE_URL1)