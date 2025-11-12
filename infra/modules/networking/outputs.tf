# Networking Outputs
output "network_id" { value = google_compute_network.vpc.id }
output "network_name" { value = google_compute_network.vpc.name }
output "network_self_link" { value = google_compute_network.vpc.self_link }
output "subnet_ids" { value = [for s in google_compute_subnetwork.subnets : s.id] }
output "subnet_names" { value = [for s in google_compute_subnetwork.subnets : s.name] }
output "router_id" { value = google_compute_router.router.id }
output "nat_id" { value = google_compute_router_nat.nat.id }
