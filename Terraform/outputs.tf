output "instance_public_ip" {
  value = aws_instance.this.public_ip
}

output "elastic_ip" {
  value = aws_eip.this.public_ip
}