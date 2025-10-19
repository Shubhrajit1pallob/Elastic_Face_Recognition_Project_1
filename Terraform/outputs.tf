output "instance_public_ip" {
  value = aws_instance.this.public_ip
}

output "elastic_ip" {
  value = aws_eip.this.public_ip
}

output "web_to_app_queue_url" {
  value = aws_sqs_queue.web_to_app.id
}

output "app_to_web_queue_url" {
  value = aws_sqs_queue.app_to_web.id
}