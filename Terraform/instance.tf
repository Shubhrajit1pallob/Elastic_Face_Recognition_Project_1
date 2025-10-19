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
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.web_to_app.arn,
          aws_sqs_queue.app_to_web.arn
        ]
      }
    ]
  })
}