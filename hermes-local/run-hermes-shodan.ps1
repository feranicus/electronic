# run-hermes-shodan.ps1 — start Hermes (interactive chat) with the shodan-assessment
# skill mounted and the outputs folder wired up. Uses your DO Qwen as the model.
#
#   .\run-hermes-shodan.ps1 -OpenAIKey "doo_v1_..." -ShodanKey "YOUR_SHODAN_KEY"
#
param(
  [string]$OpenAIKey = $env:OPENAI_API_KEY,
  [string]$ShodanKey = $env:SHODAN_API_KEY
)
$Skill = "C:\Python SW\Linkedin Scraper\hermes-skills\shodan-assessment"
$Out   = "C:\Python SW\Linkedin Scraper\shodan-out"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

# The skill is bind-mounted OVER a subpath of the hermes_data volume so Hermes sees it
# at ~/.hermes/skills/shodan-assessment. Outputs land in .\shodan-out on Windows.
docker run -it --rm `
  -e OPENAI_API_KEY=$OpenAIKey -e OPENAI_BASE_URL=https://inference.do-ai.run/v1 `
  -e SHODAN_API_KEY=$ShodanKey `
  -v hermes_data:/root/.hermes `
  -v "${Skill}:/root/.hermes/skills/shodan-assessment" `
  -v "${Out}:/root/work" `
  hermes-local
