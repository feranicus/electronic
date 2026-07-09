output "droplet_ip" {
  value = var.create_droplet ? digitalocean_droplet.bots[0].ipv4_address : "create_droplet=false (using the existing shared droplet)"
}
output "project_id" { value = digitalocean_project.colt.id }
