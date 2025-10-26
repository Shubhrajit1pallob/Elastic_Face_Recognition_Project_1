packer {
    required_plugins {
        amazon = {
            version = "~> 1"
            source  = "github.com/hashicorp/amazon"
        }
    }
}

source "amazon-ebs" "app-tier-ami" {
    region = "us-east-1"
    instance_type = "t2.micro"
    source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd/ubuntu-*-22.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    owners      = ["099720109477"]
    most_recent = true
  }

  ami_name = "app-tier-ami"

  ssh_username = "ubuntu"

  tags = {
    Name = "app-tier-ami"
  }
}

build {
    name = "app-tier-ami-build"
    sources = ["source.amazon-ebs.app-tier-ami"]

    provisioner "shell" {
        inline = [
            "sudo mkdir -p /home/ubuntu/app-tier-app",
            "sudo chown -R ubuntu:ubuntu /home/ubuntu/app-tier-app",
            "sudo chmod -R 755 /home/ubuntu/app-tier-app"
        ]
    }

    provisioner "file" {
        source = "app-tier-files/"
        destination = "/home/ubuntu/app-tier-app"
    }

    provisioner "shell" {
        script = "app-tier.sh"
    }
}