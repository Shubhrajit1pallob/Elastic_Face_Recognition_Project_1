resource "aws_sqs_queue" "web_to_app" {
  name             = "0000000000-req-queue"
  max_message_size = 1024

  tags = {
    Name = "0000000000-req-queue"
  }
}

resource "aws_sqs_queue" "app_to_web" {
  name             = "0000000000-resp-queue"
  max_message_size = 1024

  tags = {
    Name = "0000000000-resp-queue"
  }
}

resource "aws_sqs_queue_policy" "app_to_web_policy" {
  queue_url = aws_sqs_queue.app_to_web.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "SQS:SendMessage"
        Resource  = aws_sqs_queue.app_to_web.arn
      }
    ]
  })
}

resource "aws_sqs_queue_policy" "web_to_app_policy" {
  queue_url = aws_sqs_queue.web_to_app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "SQS:SendMessage"
        Resource  = aws_sqs_queue.web_to_app.arn
      }
    ]
  })
}