# Logging infra module placeholder
resource "aws_cloudwatch_log_group" "app" {
  name              = "/digicloset/app"
  retention_in_days = 30
}
