# tofu/ — OpenTofu for the Colt bots (KISS, non-destructive)

Declares the *cloud* infra as code. **It never touches your existing shared droplet** —
`create_droplet` defaults to `false`, and `prevent_destroy` guards the optional dedicated host.

## Use
```bash
export DIGITALOCEAN_TOKEN=dop_v1_xxx     # DO API token (read+write)
cd tofu
tofu init
tofu plan                                 # review — with defaults it only creates a DO "project"
# to stand up a clean dedicated host later:
tofu plan  -var create_droplet=true -var 'ssh_key_fingerprints=["<fp>"]' -var 'ssh_allow_cidrs=["<your-ip>/32"]'
tofu apply -var create_droplet=true ...
```

## What it manages
- a DigitalOcean **project** (grouping) — safe, additive
- OPTIONAL **dedicated droplet** + **least-privilege firewall** (SSH from your IP, outbound open) + **DNS**

## Notes
- State (`*.tfstate`) is gitignored. For team use, move to a remote backend (DO Spaces, S3-compatible).
- The running bots keep deploying via `deploy.py --reuse` onto whichever host you point at —
  OpenTofu here is for reproducible *infrastructure*, not the app rollout.
