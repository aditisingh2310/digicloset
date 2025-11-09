package policy
deny[msg] {
  input.resource.type == "aws_s3_bucket"
  input.resource.public == true
  msg = "Public S3 buckets are not allowed"
}
