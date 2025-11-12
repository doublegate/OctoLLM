# OctoLLM Development Environment
# This file provisions all infrastructure for the dev environment

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "gcs" {
    bucket = "octollm-dev-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local variables
locals {
  environment = "dev"
  labels = {
    project     = "octollm"
    environment = local.environment
    managed_by  = "terraform"
    cost_center = "engineering"
  }
}

# Networking
module "networking" {
  source = "../../modules/networking"

  project_id   = var.project_id
  network_name = "octollm-dev-vpc"
  region       = var.region

  subnets = {
    gke = {
      ip_cidr_range = "10.0.0.0/20"  # 4,096 IPs
      secondary_ranges = {
        pods     = "10.4.0.0/14"  # 262,144 pod IPs
        services = "10.8.0.0/20"  # 4,096 service IPs
      }
    }
  }

  firewall_rules = [
    {
      name      = "allow-internal"
      direction = "INGRESS"
      ranges    = ["10.0.0.0/8"]
      allow     = [{ protocol = "all", ports = [] }]
      deny      = []
    }
  ]
}

# GKE Cluster
module "gke" {
  source = "../../modules/gke"

  project_id         = var.project_id
  region             = var.region
  cluster_name       = "octollm-dev-cluster"
  kubernetes_version = "1.28"
  environment        = local.environment

  network_name                  = module.networking.network_name
  subnet_name                   = "octollm-dev-vpc-gke"
  pods_secondary_range_name     = "pods"
  services_secondary_range_name = "services"

  enable_private_cluster = false  # Public for dev (easier access)

  node_pools = {
    default = {
      machine_type                = "e2-standard-2"  # 2 vCPU, 8GB RAM
      initial_node_count          = 1
      min_nodes                   = 1
      max_nodes                   = 3
      disk_size_gb                = 50
      disk_type                   = "pd-standard"
      preemptible                 = true  # 60-91% discount
      spot                        = false
      auto_repair                 = true
      auto_upgrade                = true
      enable_secure_boot          = true
      enable_integrity_monitoring = true
      labels                      = {}
      taints                      = []
      tags                        = []
    }
  }

  enable_binary_authorization = false  # Dev: disable for flexibility
  security_posture_mode       = "BASIC"

  labels             = local.labels
  network_depends_on = module.networking.network_id
}

# Cloud SQL PostgreSQL
module "database" {
  source = "../../modules/database"

  project_id       = var.project_id
  region           = var.region
  instance_name    = "octollm-dev-postgres"
  postgres_version = "POSTGRES_15"
  environment      = local.environment

  tier                  = "db-f1-micro"  # 1 vCPU, 2GB RAM
  disk_size             = 20
  disk_type             = "PD_SSD"
  disk_autoresize       = true
  deletion_protection   = false  # Dev: allow deletion

  high_availability = false  # Dev: no HA needed
  read_replicas     = 0

  backup_enabled    = true
  backup_start_time = "03:00"
  retention_days    = 7
  point_in_time_recovery = false  # Dev: disable PITR

  network_id      = module.networking.network_id
  enable_public_ip = true  # Dev: enable for easier access

  database_name = "octollm"
  database_user = "octollm"

  max_connections = "100"
  shared_buffers  = "256MB"

  labels             = local.labels
  network_depends_on = module.networking.network_id
}

# Memorystore for Redis
module "redis" {
  source = "../../modules/redis"

  project_id    = var.project_id
  region        = var.region
  instance_name = "octollm-dev-redis"
  environment   = local.environment

  tier           = "BASIC"  # Dev: no HA
  memory_size_gb = 2
  redis_version  = "REDIS_7_0"

  network_id = module.networking.network_id

  persistence_mode    = "RDB"
  rdb_snapshot_period = "ONE_HOUR"

  transit_encryption_mode = "SERVER_AUTHENTICATION"
  auth_enabled            = true

  read_replicas_mode = "READ_REPLICAS_DISABLED"
  replica_count      = 0

  prevent_destroy = false  # Dev: allow deletion

  labels = local.labels
}

# Cloud Storage Buckets
module "storage" {
  source = "../../modules/storage"

  project_id  = var.project_id
  environment = local.environment

  buckets = {
    backups = {
      name          = "octollm-dev-backups"
      location      = var.region
      storage_class = "STANDARD"
      versioning    = true
      encryption_key = ""  # Use Google-managed keys
      lifecycle_rules = [
        {
          action = {
            type          = "Delete"
            storage_class = ""
          }
          condition = {
            age                = 90  # Delete after 90 days
            num_newer_versions = 0
            with_state         = ""
          }
        }
      ]
      labels = {}
    }
    logs = {
      name          = "octollm-dev-logs"
      location      = var.region
      storage_class = "STANDARD"
      versioning    = false
      encryption_key = ""
      lifecycle_rules = [
        {
          action = {
            type          = "SetStorageClass"
            storage_class = "NEARLINE"
          }
          condition = {
            age                = 30
            num_newer_versions = 0
            with_state         = ""
          }
        },
        {
          action = {
            type          = "Delete"
            storage_class = ""
          }
          condition = {
            age                = 365
            num_newer_versions = 0
            with_state         = ""
          }
        }
      ]
      labels = {}
    }
  }

  labels = local.labels
}
