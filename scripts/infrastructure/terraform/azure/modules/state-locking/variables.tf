variable "lock_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking"
  type        = string
  default     = "terraform-locks"
}

variable "environment" {
  description = "Environment name (e.g., sit, uat, prod)"
  type        = string
  default     = "sit"
}
