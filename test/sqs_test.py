import boto3

# Replace with your actual queue URL
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue'

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
    
def purge_queue():
    while True:
        response = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=2)
        messages = response.get('Messages', [])
        if not messages:
            print("Queue is empty.")
            break
        for msg in messages:
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
            print("Deleted message:", msg['Body'])
    
if __name__ == "__main__":
    # Test sending
    # send_message("Hello SQS!")

    # Test receiving
    # body, handle = receive_message()

    # # Test deleting
    # if handle:
    #     delete_message(handle)
    
    purge_queue()