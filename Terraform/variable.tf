variable "private_key" {
  description = "The private key for ssh key pair"
  type        = string
}

variable "public_key" {
  description = "The public key for ssh key pair"
  type        = string
}

variable "region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}