from flask import Flask, request, jsonify
import os
import boto3
import csv

app = Flask(__name__)

# Initialize the s3 client
s3_client = boto3.client('s3', region_name='us-east-1')
BUCKET_NAME = '0000000000-in-bucket'

# Initialize the SimpleDB client
sdb_client = boto3.client('sdb', region_name='us-east-1')
DOMAIN_NAME = '0000000000-simpleDB'

def delete_domain():
    try:
        sdb_client.delete_domain(DomainName=DOMAIN_NAME)
        print(f"Deleted domain: {DOMAIN_NAME}")
        return True
    except Exception as e:
        print(f"Error deleting domain: {e}")
        return False

# Check if the domain exists and that domain has data
def ensure_domain_exists():
    try:
        response = sdb_client.list_domains()
        domains = response.get('DomainNames', [])

        if DOMAIN_NAME in domains:
            print(f"Domain {DOMAIN_NAME} already exists.")
            
            try:
                # Count existing items (this is a rough estimate)
                select_response = sdb_client.select(
                    SelectExpression=f'SELECT count(*) FROM `{DOMAIN_NAME}`'
                )
                if 'Items' in select_response and select_response['Items']:
                    count = int(select_response['Items'][0]['Attributes'][0]['Value'])
                    print(f"Domain currently has {count} items")
                
                    if count < 1000:
                        print(f"Domain incomplete ({count}/1000). Deleting and recreating...")
                        delete_domain()
                        domains = []  # Force recreation
                        
            except Exception as count_error:
                print(f"Could not count existing items: {count_error}")
            
        if DOMAIN_NAME not in domains:
            sdb_client.create_domain(DomainName=DOMAIN_NAME)
            print(f"Created: {DOMAIN_NAME}")
            
            print("Starting CSV population...")
            success_count = 0
            error_count = 0
            
            # Fill the domain with the initial data

            with open('Classification_Results_on_Face_Dataset.csv', newline='') as csvfile:

                reader = csv.DictReader(csvfile)
                total_rows = sum(1 for row in reader)
                print(f"Total rows to process: {total_rows}")
                
                csvfile.seek(0)
                reader = csv.DictReader(csvfile)
                
                for index, row in enumerate(reader):
                    try:
                        sdb_client.put_attributes(
                            DomainName=DOMAIN_NAME,
                            ItemName=row['Image'],
                            Attributes=[
                                {'Name': 'Results', 'Value': row['Results'], 'Replace': True}
                            ]
                        )
                        success_count += 1
                        
                        # Progress logging every 100 records
                        if success_count % 100 == 0:
                            print(f"Successfully populated {success_count}/{total_rows} records...")
                            
                    except Exception as record_error:
                        error_count += 1
                        print(f"Error inserting record {index + 1} (Image: {row.get('Image', 'Unknown')}): {record_error}")
                        
                        # Add a small delay if we're hitting rate limits
                        if "throttling" in str(record_error).lower() or "rate" in str(record_error).lower():
                            print("Rate limiting detected, adding delay...")
                            import time
                            time.sleep(0.1)
                
            print(f"CSV population complete!")
            print(f"Total records processed: {success_count + error_count}")
            print(f"Successful insertions: {success_count}")
            print(f"Failed insertions: {error_count}")
            
    except Exception as e:
        print(f"Error ensuring domain exists: {e}")
        raise e
    
    return True

ensure_domain_exists()

@app.route("/", methods=['GET'])
def health_check():
    return "Face Recognition Service is running!"

@app.route("/", methods=['GET', 'POST'])
def handle_request():
    
    if 'inputFile' not in request.files:
        return jsonify({
            "error": "No file part in the request"
        }), 400  
    
    file = request.files['inputFile']
    
    filename = file.filename

    # The block to upload the file to s3.
    try:
        s3_client.upload_fileobj(file, BUCKET_NAME, filename)
        
        response = sdb_client.get_attributes(
                DomainName=DOMAIN_NAME,
                ItemName=filename,
                AttributeNames=['Results']
            )
        
        if 'Attributes' in response and response['Attributes']:
            result = response['Attributes'][0]['Value']
            print(f"File: {filename},{result}")

            return f"{filename}:{result}", 200, {"Content-Type": "text/plain"}
        else:
            return jsonify({
                "error": f"No results found for file: {filename}"
            }), 404
                
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
        

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0', threaded=True)