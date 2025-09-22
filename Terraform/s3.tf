resource "aws_s3_bucket" "capstone_bucket" {
  bucket = "0000000000-in-bucket"
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.capstone_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "this" {
  bucket     = aws_s3_bucket.capstone_bucket.id
  depends_on = [aws_s3_bucket_public_access_block.this]

  policy = jsonencode({
    Version : "2012-10-17"
    Statement : [
      {
        Sid       = "AllowAllS3ActionsInUserAccount",
        Principal = "*",
        Effect    = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ],
        Resource = "${aws_s3_bucket.capstone_bucket.arn}/*",
      }
    ]
  })
}