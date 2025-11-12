# GKE Module Variables

# Basic Configuration
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the cluster"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Minimum Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

# Network Configuration
variable "network_name" {
  description = "Name of the VPC network"
  type        = string
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
}

variable "pods_secondary_range_name" {
  description = "Name of the secondary range for pods"
  type        = string
  default     = "pods"
}

variable "services_secondary_range_name" {
  description = "Name of the secondary range for services"
  type        = string
  default     = "services"
}

# Private Cluster Configuration
variable "enable_private_cluster" {
  description = "Enable private cluster (nodes have no public IPs)"
  type        = bool
  default     = false
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint (control plane not accessible via public IP)"
  type        = bool
  default     = false
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the Kubernetes master (if private cluster)"
  type        = string
  default     = "172.16.0.0/28"
}

variable "authorized_networks" {
  description = "List of authorized networks that can access the Kubernetes API"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

# Node Pool Configuration
variable "node_pools" {
  description = "Map of node pool configurations"
  type = map(object({
    machine_type            = string
    initial_node_count      = number
    min_nodes               = number
    max_nodes               = number
    disk_size_gb            = number
    disk_type               = string
    preemptible             = bool
    spot                    = bool
    auto_repair             = bool
    auto_upgrade            = bool
    enable_secure_boot      = bool
    enable_integrity_monitoring = bool
    labels                  = map(string)
    taints = list(object({
      key    = string
      value  = string
      effect = string
    }))
    tags = list(string)
  }))
  default = {
    default = {
      machine_type            = "e2-standard-4"
      initial_node_count      = 1
      min_nodes               = 1
      max_nodes               = 5
      disk_size_gb            = 100
      disk_type               = "pd-standard"
      preemptible             = false
      spot                    = false
      auto_repair             = true
      auto_upgrade            = true
      enable_secure_boot      = true
      enable_integrity_monitoring = true
      labels                  = {}
      taints                  = []
      tags                    = []
    }
  }
}

variable "node_service_account" {
  description = "Service account for GKE nodes (if empty, creates one)"
  type        = string
  default     = ""
}

variable "enable_artifact_registry_access" {
  description = "Grant node SA access to Artifact Registry (for pulling images)"
  type        = bool
  default     = true
}

# Add-ons Configuration
variable "enable_network_policy" {
  description = "Enable Kubernetes Network Policy"
  type        = bool
  default     = true
}

variable "enable_dns_cache" {
  description = "Enable NodeLocal DNS Cache"
  type        = bool
  default     = true
}

variable "enable_filestore_csi_driver" {
  description = "Enable Filestore CSI driver"
  type        = bool
  default     = false
}

variable "enable_gcs_fuse_csi_driver" {
  description = "Enable GCS FUSE CSI driver"
  type        = bool
  default     = false
}

variable "enable_vertical_pod_autoscaling" {
  description = "Enable Vertical Pod Autoscaling"
  type        = bool
  default     = true
}

# Monitoring and Logging
variable "monitoring_components" {
  description = "List of monitoring components to enable"
  type        = list(string)
  default     = ["SYSTEM_COMPONENTS", "WORKLOADS"]
}

variable "enable_managed_prometheus" {
  description = "Enable managed Prometheus"
  type        = bool
  default     = false
}

variable "logging_components" {
  description = "List of logging components to enable"
  type        = list(string)
  default     = ["SYSTEM_COMPONENTS", "WORKLOADS"]
}

# Security Configuration
variable "enable_binary_authorization" {
  description = "Enable Binary Authorization (require signed images)"
  type        = bool
  default     = false
}

variable "security_posture_mode" {
  description = "Security posture mode (DISABLED, BASIC, ENTERPRISE)"
  type        = string
  default     = "BASIC"
}

variable "security_posture_vulnerability_mode" {
  description = "Vulnerability scanning mode (VULNERABILITY_DISABLED, VULNERABILITY_BASIC, VULNERABILITY_ENTERPRISE)"
  type        = string
  default     = "VULNERABILITY_BASIC"
}

# Maintenance Configuration
variable "maintenance_start_time" {
  description = "Start time for maintenance window (HH:MM format, UTC)"
  type        = string
  default     = "03:00"
}

# Notification Configuration
variable "enable_notification_config" {
  description = "Enable cluster event notifications to Pub/Sub"
  type        = bool
  default     = false
}

variable "notification_topic" {
  description = "Pub/Sub topic for cluster notifications"
  type        = string
  default     = ""
}

# Labels
variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# Dependencies
variable "network_depends_on" {
  description = "Dependencies for network resources"
  type        = any
  default     = null
}
