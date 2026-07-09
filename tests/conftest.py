import os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "hermes-skills" / "shodan-assessment" / "scripts"))
os.environ.setdefault("COLT_BOT_PASSWORD", "test-secret-123")
os.environ.setdefault("REQUIRE_2FA", "0")   # default off; the OTP test flips it on
