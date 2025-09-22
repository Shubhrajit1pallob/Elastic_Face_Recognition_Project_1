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

# Check if the domain exists and that domain has data
def ensure_domain_exists():
    domains = sdb_client.list_domains()['DomainNames']
    if DOMAIN_NAME not in domains:
        sdb_client.create_domain(DomainName=DOMAIN_NAME)
        print(f"Created: {DOMAIN_NAME}")
    else:
        print(f"Domain {DOMAIN_NAME} already exists.")
        return True
        
    # Fill the domain with the initial data

    with open('Classification_Results_on_Face_Dataset.csv', newline='') as csvfile:

        reader = csv.DictReader(csvfile)
        for row in reader:
            sdb_client.put_attributes(
                DomainName=DOMAIN_NAME,
                ItemName=row['Image'],  # e.g., 'test_000'
                Attributes=[
                    {'Name': 'Results', 'Value': row['Results'], 'Replace': True}
                ]
            )

    return True

@app.route("/", methods=['POST'])
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
        
        if ensure_domain_exists():
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
        else:
            return jsonify({
                "error": "SimpleDB domain could not be ensured."
            }), 500
                
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
        

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0', threaded=True)