# test-shodan.ps1 — smoke-test the shodan-assessment pipeline INSIDE the hermes-local
# image, without the Hermes chat. Proves recon + deck end-to-end.
#
#   .\test-shodan.ps1 -Seed "keb.de" -ShodanKey "YOUR_SHODAN_KEY"
#   .\test-shodan.ps1 -Seed "AS211483"           # no key -> filters.md only
#
param(
  [Parameter(Mandatory=$true)][string]$Seed,
  [string]$ShodanKey = $env:SHODAN_API_KEY
)
$ErrorActionPreference = "Stop"
$Skill = "C:\Python SW\Linkedin Scraper\hermes-skills\shodan-assessment"
$Out   = "C:\Python SW\Linkedin Scraper\shodan-out"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Write-Host "==> building hermes-local image (first build is slow) ..." -ForegroundColor Cyan
docker build -t hermes-local "C:\Python SW\Linkedin Scraper\hermes-local"

$safe = ($Seed -replace '[^A-Za-z0-9.]','_')
if ([string]::IsNullOrWhiteSpace($ShodanKey)) {
  Write-Host "==> no Shodan key -> generating filters.md only (no live scan)" -ForegroundColor Yellow
  docker run --rm -v "${Skill}:/skill" -v "${Out}:/out" -w /skill hermes-local `
    python3 scripts/shodan_recon.py --seed "$Seed" --outdir /out --print-filters
} else {
  Write-Host "==> recon + deck for '$Seed' ..." -ForegroundColor Cyan
  docker run --rm -e SHODAN_API_KEY=$ShodanKey -v "${Skill}:/skill" -v "${Out}:/out" -w /skill hermes-local `
    sh -c "python3 scripts/shodan_recon.py --seed '$Seed' --outdir /out && node scripts/build_findings_deck.js /out/findings.json '/out/${safe}_Shodan_Findings.pptx'"
}
Write-Host "==> done. Open the outputs here: $Out" -ForegroundColor Green
