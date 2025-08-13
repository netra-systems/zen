output "vpc_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "Main subnet ID"
  value       = google_compute_subnetwork.main.id
}

output "subnet_name" {
  description = "Main subnet name"
  value       = google_compute_subnetwork.main.name
}

output "vpc_connector_id" {
  description = "VPC connector ID for Cloud Run"
  value       = google_vpc_access_connector.connector.id
}

output "vpc_connector_name" {
  description = "VPC connector name"
  value       = google_vpc_access_connector.connector.name
}

output "lb_ip_address" {
  description = "Load balancer IP address"
  value       = google_compute_global_address.lb_ip.address
}

output "lb_url_map_id" {
  description = "Load balancer URL map ID"
  value       = google_compute_url_map.lb.id
}

output "private_vpc_connection" {
  description = "Private VPC connection for databases"
  value       = google_service_networking_connection.private_vpc_connection.id
}

output "router_name" {
  description = "Router name for NAT"
  value       = google_compute_router.router.name
}

output "nat_name" {
  description = "Cloud NAT name"
  value       = google_compute_router_nat.nat.name
}

output "security_policy_id" {
  description = "Cloud Armor security policy ID"
  value       = var.enable_cloud_armor ? google_compute_security_policy.policy[0].id : ""
}