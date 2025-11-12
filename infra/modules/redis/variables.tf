# Redis Variables
variable "project_id" { type = string }
variable "region" { type = string }
variable "instance_name" { type = string }
variable "environment" { type = string }
variable "tier" { type = string; default = "BASIC" }  # BASIC or STANDARD_HA
variable "memory_size_gb" { type = number; default = 2 }
variable "redis_version" { type = string; default = "REDIS_7_0" }
variable "network_id" { type = string }
variable "connect_mode" { type = string; default = "DIRECT_PEERING" }
variable "redis_configs" { type = map(string); default = {} }
variable "maintenance_day" { type = string; default = "SUNDAY" }
variable "maintenance_hour" { type = number; default = 3 }
variable "persistence_mode" { type = string; default = "RDB" }
variable "rdb_snapshot_period" { type = string; default = "ONE_HOUR" }
variable "transit_encryption_mode" { type = string; default = "SERVER_AUTHENTICATION" }
variable "auth_enabled" { type = bool; default = true }
variable "read_replicas_mode" { type = string; default = "READ_REPLICAS_DISABLED" }
variable "replica_count" { type = number; default = 0 }
variable "prevent_destroy" { type = bool; default = true }
variable "labels" { type = map(string); default = {} }
