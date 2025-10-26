import boto3
import time

# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

# Your queue URL
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue'

def check_queue():
    print(f"Checking queue: {QUEUE_URL}")
    
    while True:
        try:
            # Get queue attributes
            attrs = sqs.get_queue_attributes(
                QueueUrl=QUEUE_URL,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            msg_count = int(attrs['Attributes']['ApproximateNumberOfMessages'])
            print(f"Messages in queue: {msg_count}")

            # Receive messages
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=2,
                VisibilityTimeout=0  # Make messages immediately visible again
            )
            
            messages = response.get('Messages', [])
            if not messages:
                print("No messages found")
                time.sleep(2)
                continue
                
            print("\nFound messages:")
            for msg in messages:
                print(f"MessageId: {msg['MessageId']}")
                print(f"Body: {msg['Body']}")
                print("---")
                
        except KeyboardInterrupt:
            print("\nStopping queue check...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    check_queue()