# KISS OpenTofu for the Colt bots' CLOUD infra.
# SAFE: create_droplet defaults to false, so this NEVER touches your existing shared droplet.
# Auth: export DIGITALOCEAN_TOKEN=dop_v1_xxx   (then: tofu init && tofu plan && tofu apply)

terraform {
  required_version = ">= 1.6"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
  # For team use, switch to a remote backend (DO Spaces / S3-compatible) instead of local state.
}

provider "digitalocean" {}   # reads DIGITALOCEAN_TOKEN from the environment

# Group everything under one DO project (safe, additive).
resource "digitalocean_project" "colt" {
  name        = var.project_name
  description = "Colt cyber pre-sales bots"
  purpose     = "Service or API"
  environment = "Production"
}

# OPTIONAL dedicated bot host — flip create_droplet=true when you outgrow the shared box.
resource "digitalocean_droplet" "bots" {
  count    = var.create_droplet ? 1 : 0
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-24-04-x64"
  ssh_keys = var.ssh_key_fingerprints
  tags     = ["colt-bots"]
  lifecycle { prevent_destroy = true }
}

# Least-privilege firewall for the dedicated host only: SSH from YOUR IP, outbound open, nothing else in.
resource "digitalocean_firewall" "bots" {
  count       = var.create_droplet ? 1 : 0
  name        = "colt-bots-fw"
  droplet_ids = [digitalocean_droplet.bots[0].id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.ssh_allow_cidrs
  }
  outbound_rule { protocol = "tcp"  port_range = "1-65535" destination_addresses = ["0.0.0.0/0", "::/0"] }
  outbound_rule { protocol = "udp"  port_range = "1-65535" destination_addresses = ["0.0.0.0/0", "::/0"] }
  outbound_rule { protocol = "icmp"                        destination_addresses = ["0.0.0.0/0", "::/0"] }
}

resource "digitalocean_project_resources" "colt" {
  count     = var.create_droplet ? 1 : 0
  project   = digitalocean_project.colt.id
  resources = [digitalocean_droplet.bots[0].urn]
}

# OPTIONAL DNS (only if the domain is managed in DigitalOcean).
resource "digitalocean_record" "bots" {
  count  = var.dns_domain != "" && var.create_droplet ? 1 : 0
  domain = var.dns_domain
  type   = "A"
  name   = var.dns_record
  value  = digitalocean_droplet.bots[0].ipv4_address
  ttl    = 300
}
