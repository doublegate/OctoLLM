# GKE (Google Kubernetes Engine) Module
# Creates a regional GKE cluster with autoscaling, monitoring, and security features

# Regional GKE Cluster (multi-AZ for HA)
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region  # Regional cluster (spans multiple zones)

  # Minimum version (auto-upgrades to latest patch)
  min_master_version = var.kubernetes_version

  # Remove default node pool (we'll create custom node pools)
  remove_default_node_pool = true
  initial_node_count       = 1

  # Network configuration
  network    = var.network_name
  subnetwork = var.subnet_name

  # IP allocation for pods and services (VPC-native cluster)
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_secondary_range_name
    services_secondary_range_name = var.services_secondary_range_name
  }

  # Workload Identity (best practice: bind K8s service accounts to GCP service accounts)
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Private cluster configuration (optional, recommended for prod)
  dynamic "private_cluster_config" {
    for_each = var.enable_private_cluster ? [1] : []
    content {
      enable_private_nodes    = true
      enable_private_endpoint = var.enable_private_endpoint
      master_ipv4_cidr_block  = var.master_ipv4_cidr_block
    }
  }

  # Authorized networks (who can access the Kubernetes API)
  dynamic "master_authorized_networks_config" {
    for_each = var.enable_private_cluster && length(var.authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  # Add-ons
  addons_config {
    http_load_balancing {
      disabled = false  # Enable Ingress controller
    }

    horizontal_pod_autoscaling {
      disabled = false  # Enable HPA (auto-scale pods based on CPU/memory)
    }

    network_policy_config {
      disabled = !var.enable_network_policy
    }

    dns_cache_config {
      enabled = var.enable_dns_cache
    }

    gcp_filestore_csi_driver_config {
      enabled = var.enable_filestore_csi_driver
    }

    gcs_fuse_csi_driver_config {
      enabled = var.enable_gcs_fuse_csi_driver
    }
  }

  # Vertical Pod Autoscaling (auto-adjust resource requests)
  vertical_pod_autoscaling {
    enabled = var.enable_vertical_pod_autoscaling
  }

  # Maintenance window (when auto-upgrades/repairs occur)
  maintenance_policy {
    daily_maintenance_window {
      start_time = var.maintenance_start_time  # e.g., "03:00" (3 AM UTC)
    }
  }

  # Monitoring and logging
  monitoring_config {
    enable_components = var.monitoring_components
    managed_prometheus {
      enabled = var.enable_managed_prometheus
    }
  }

  logging_config {
    enable_components = var.logging_components
  }

  # Resource labels
  resource_labels = merge(
    var.labels,
    {
      environment = var.environment
      component   = "kubernetes"
    }
  )

  # Binary Authorization (require signed container images)
  dynamic "binary_authorization" {
    for_each = var.enable_binary_authorization ? [1] : []
    content {
      evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
    }
  }

  # Security posture configuration
  security_posture_config {
    mode               = var.security_posture_mode
    vulnerability_mode = var.security_posture_vulnerability_mode
  }

  # Notification configuration (cluster events to Pub/Sub)
  dynamic "notification_config" {
    for_each = var.enable_notification_config ? [1] : []
    content {
      pubsub {
        enabled = true
        topic   = var.notification_topic
      }
    }
  }

  # Lifecycle (prevent accidental deletion in prod)
  lifecycle {
    ignore_changes = [
      initial_node_count,
      min_master_version  # Allow auto-upgrades
    ]
  }

  # Depends on network being created
  depends_on = [
    var.network_depends_on
  ]
}

# Node Pool (custom node configuration)
resource "google_container_node_pool" "primary_nodes" {
  for_each = var.node_pools

  name       = each.key
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = each.value.initial_node_count

  # Autoscaling configuration
  autoscaling {
    min_node_count = each.value.min_nodes
    max_node_count = each.value.max_nodes
  }

  # Auto-repair and auto-upgrade
  management {
    auto_repair  = each.value.auto_repair
    auto_upgrade = each.value.auto_upgrade
  }

  # Node configuration
  node_config {
    preemptible  = each.value.preemptible
    spot         = each.value.spot
    machine_type = each.value.machine_type

    # Disk configuration
    disk_size_gb = each.value.disk_size_gb
    disk_type    = each.value.disk_type

    # Service account (use least-privilege custom SA, not default)
    service_account = var.node_service_account != "" ? var.node_service_account : google_service_account.node_sa[0].email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Labels
    labels = merge(
      var.labels,
      each.value.labels,
      {
        environment = var.environment
        node_pool   = each.key
      }
    )

    # Taints (for dedicated node pools)
    dynamic "taint" {
      for_each = each.value.taints
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }

    # Metadata
    metadata = {
      disable-legacy-endpoints = "true"
      google-compute-enable-virtio-rng = "true"
    }

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Shielded Instance (secure boot)
    shielded_instance_config {
      enable_secure_boot          = each.value.enable_secure_boot
      enable_integrity_monitoring = each.value.enable_integrity_monitoring
    }

    # GCE instance tags
    tags = concat(
      ["gke-node", "${var.cluster_name}-node"],
      each.value.tags
    )

    # Resource labels
    resource_labels = merge(
      var.labels,
      {
        environment = var.environment
        node_pool   = each.key
      }
    )
  }

  # Lifecycle
  lifecycle {
    ignore_changes = [
      node_config[0].labels,
      node_config[0].taint
    ]
  }

  depends_on = [
    google_container_cluster.primary
  ]
}

# Service Account for Nodes (least privilege)
resource "google_service_account" "node_sa" {
  count = var.node_service_account == "" ? 1 : 0

  account_id   = "${var.cluster_name}-node-sa"
  display_name = "GKE Node Service Account for ${var.cluster_name}"
  project      = var.project_id
}

# Grant minimal permissions to node service account
resource "google_project_iam_member" "node_sa_log_writer" {
  count = var.node_service_account == "" ? 1 : 0

  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.node_sa[0].email}"
}

resource "google_project_iam_member" "node_sa_metric_writer" {
  count = var.node_service_account == "" ? 1 : 0

  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.node_sa[0].email}"
}

resource "google_project_iam_member" "node_sa_monitoring_viewer" {
  count = var.node_service_account == "" ? 1 : 0

  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.node_sa[0].email}"
}

resource "google_project_iam_member" "node_sa_artifact_registry_reader" {
  count = var.node_service_account == "" && var.enable_artifact_registry_access ? 1 : 0

  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.node_sa[0].email}"
}
