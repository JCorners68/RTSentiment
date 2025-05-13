output "dynamodb_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table used for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.arn
}
