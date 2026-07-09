variable "project_name" {
  type    = string
  default = "colt-bots"
}
variable "region" {
  type    = string
  default = "fra1"
}
variable "droplet_name" {
  type    = string
  default = "colt-bots-fra1"
}
variable "droplet_size" {
  type    = string
  default = "s-2vcpu-4gb"
}
variable "create_droplet" {
  type    = bool
  default = false # SAFE default: never touches the existing shared droplet
}
variable "ssh_key_fingerprints" {
  type    = list(string)
  default = [] # doctl compute ssh-key list
}
variable "ssh_allow_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"] # tighten to your IP in production
}
variable "dns_domain" {
  type    = string
  default = ""
}
variable "dns_record" {
  type    = string
  default = "bots"
}
