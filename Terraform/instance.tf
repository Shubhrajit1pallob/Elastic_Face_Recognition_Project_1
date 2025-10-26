locals {
  public_key_content  = var.public_key != "" ? var.public_key : file("/Users/shawn47/.ssh/id_ed25519.pub")
  private_key_content = var.private_key != "" ? var.private_key : file("/Users/shawn47/.ssh/id_ed25519")
}

data "aws_ami" "ubuntu" {

  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.public_subnet.id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.public.id]
  key_name                    = aws_key_pair.this.key_name
  iam_instance_profile        = aws_iam_instance_profile.app_tier_profile.name

  root_block_device {
    volume_size           = 8
    volume_type           = "gp2"
    delete_on_termination = true
  }

  tags = {
    Name = "web-instance"
  }
}

resource "aws_key_pair" "this" {
  key_name   = "cse543-project1-key"
  public_key = local.public_key_content
}

resource "aws_eip" "this" {
  instance = aws_instance.this.id

  tags = {
    Name = "web-instance-eip"
  }
}

resource "aws_iam_policy" "sqs_access" {
  name = "SQSAccessPolicy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_sqs_queue.web_to_app.arn,
          aws_sqs_queue.app_to_web.arn,
          aws_s3_bucket.capstone_bucket.arn,
          "${aws_s3_bucket.capstone_bucket.arn}/*",
          aws_s3_bucket.output_bucket.arn,
          "${aws_s3_bucket.output_bucket.arn}/*"
        ]
      }
    ]
  })
}


resource "aws_iam_role" "app_tier_role" {
  name = "app-tier-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "app_tier_role_policy_attachment" {
  role       = aws_iam_role.app_tier_role.name
  policy_arn = aws_iam_policy.sqs_access.arn
}

resource "aws_iam_instance_profile" "app_tier_profile" {
  name = "app-tier-profile"
  role = aws_iam_role.app_tier_role.name
}