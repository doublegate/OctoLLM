# Google Cloud Storage Module

resource "google_storage_bucket" "buckets" {
  for_each = var.buckets

  name          = each.value.name
  location      = each.value.location
  storage_class = each.value.storage_class
  project       = var.project_id

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = each.value.versioning
  }

  dynamic "lifecycle_rule" {
    for_each = each.value.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lookup(lifecycle_rule.value.action, "storage_class", null)
      }
      condition {
        age                   = lookup(lifecycle_rule.value.condition, "age", null)
        num_newer_versions    = lookup(lifecycle_rule.value.condition, "num_newer_versions", null)
        with_state            = lookup(lifecycle_rule.value.condition, "with_state", null)
      }
    }
  }

  encryption {
    default_kms_key_name = each.value.encryption_key
  }

  labels = merge(
    var.labels,
    each.value.labels,
    {
      environment = var.environment
      component   = "storage"
    }
  )
}
