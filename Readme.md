# CSE 546 Project 1: Cloud-Based Face Recognition Web Service

## Overview

This project implements a cloud-based web service for face recognition using AWS resources. Users can upload image files via HTTP, and the server responds with the recognition result in plain text. The system uses AWS S3 for file storage and AWS SimpleDB for storing and retrieving recognition results.

## Features

- Flask-based web server for handling HTTP POST requests
- Stores uploaded files in AWS S3
- Retrieves recognition results from AWS SimpleDB
- Returns results in `<filename>:<prediction_results>` plain text format
- Infrastructure provisioned using Terraform (EC2, VPC, S3, SimpleDB, Security Groups)

## Directory Structure

```text
Project1/
├── Classification Results on Face Dataset (1000 images).csv
├── CSE546-SPRING-2025/
│   ├── autograder.py
│   ├── class_roster.csv
│   ├── cloudwatch.py
│   ├── grade_project1.py
│   ├── README.md
│   ├── test_zip_contents.sh
│   ├── utils.py
│   ├── validate_permission_policies.py
│   ├── workload_generator.py
│   └── submissions/
│       └── server.py
└── Terraform/
    ├── instance.tf
    ├── network.tf
    ├── provider.tf
    └── s3.tf
```

## Setup Instructions

### 1. AWS Resources

- Use Terraform scripts in the `Terraform/` directory to provision:
  - EC2 instance (Ubuntu, t2.micro)
  - VPC, subnet, internet gateway, route table, security group
  - S3 bucket for file storage
  - (Optional) Elastic IP for static public IP

### 2. Web Server

- The Flask server (`server.py`) handles file uploads and recognition requests.
- Configure AWS credentials for `boto3` (via environment variables or `~/.aws/credentials`).

### 3. Usage

- Start the Flask server (for development):

  ```bash
  python server.py
  ```

- For production and concurrency, use Gunicorn:

  ```bash
  gunicorn -w 4 -b 0.0.0.0:8000 server:app
  ```

- Upload an image file using `curl`:

  ```bash
  curl -F "inputFile=@test_000.jpg" http://<EC2_PUBLIC_IP>:8000/
  ```

- The server responds with:

  ```text
  test_000:Paul
  ```

## Notes

- Recognition results are stored in SimpleDB, populated from the CSV file.
- S3 bucket is private by default; EC2 instance must have an IAM role with S3 access.
- Security group allows inbound traffic on port 8000 for HTTP and port 22 for SSH.

## Authors

- Kritshekhar Jha (Autograder and scripts)
- Shubhrajit Pallob(Infrastructure and server implementation)

## License

MIT License
