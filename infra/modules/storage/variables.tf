# Storage Variables
variable "project_id" { type = string }
variable "environment" { type = string }
variable "buckets" {
  type = map(object({
    name          = string
    location      = string
    storage_class = string
    versioning    = bool
    encryption_key = string
    lifecycle_rules = list(object({
      action = object({
        type          = string
        storage_class = string
      })
      condition = object({
        age                = number
        num_newer_versions = number
        with_state         = string
      })
    }))
    labels = map(string)
  }))
}
variable "labels" { type = map(string); default = {} }
