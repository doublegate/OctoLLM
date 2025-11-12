# Networking Variables
variable "project_id" { type = string }
variable "network_name" { type = string }
variable "region" { type = string }
variable "subnets" {
  type = map(object({
    ip_cidr_range    = string
    secondary_ranges = map(string)
  }))
}
variable "firewall_rules" {
  type = list(object({
    name      = string
    direction = string
    ranges    = list(string)
    allow     = list(object({ protocol = string, ports = list(string) }))
    deny      = list(object({ protocol = string, ports = list(string) }))
  }))
  default = []
}
