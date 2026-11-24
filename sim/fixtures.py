"""Info fixtures for the simulator: sim/fixtures/NAME.json, gitignored.

A fixture is {"at": "HH:MM", "info": {...}}. "at" is the clock time the
screens see when it starts, so train departures still make sense later on.
"""
import datetime
import json
import sys
import urllib.request
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PROJECT_DIR = FIXTURES_DIR.parent.parent
FETCH_TIMEOUT_S = 10


class Fixture:
  def __init__(self, path: Path, at: str, info: dict) -> None:
    self.path = path
    self.at = at
    self.info = info


def parse_at(at: str) -> tuple[int, int]:
  h, m = at.split(":")
  return int(h), int(m)


def load(path: Path) -> Fixture:
  data = json.loads(path.read_text())
  if not isinstance(data, dict) or not isinstance(data.get("info"), dict) or not isinstance(data.get("at"), str):
    raise ValueError(f'{path.name} should look like {{"at": "HH:MM", "info": {{...}}}}')
  parse_at(data["at"])
  return Fixture(path, data["at"], data["info"])


def find(name: str | None) -> Path | None:
  """NAME or NAME.json in sim/fixtures, else the most recently modified one"""
  if name is not None:
    path = FIXTURES_DIR / (name if name.endswith(".json") else f"{name}.json")
    if not path.exists():
      available = ", ".join(sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))) or "none"
      raise FileNotFoundError(f"no fixture {path.name} in {FIXTURES_DIR} (available: {available})")
    return path
  paths = sorted(FIXTURES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
  return paths[-1] if paths else None


def info_url() -> str:
  sys.path.insert(0, str(PROJECT_DIR))
  try:
    import proj_secrets
  except ImportError:
    raise RuntimeError("proj_secrets.py is missing. copy proj_secrets.py.example and fill it in") from None
  # keep in sync with info_url in main.py
  return f"https://trainledazure.vercel.app/api/localinfo?code={proj_secrets.WEB_AUTH}&trainFrom={proj_secrets.TRAINS_FROM}&trainTo={proj_secrets.TRAINS_TO}&weather={proj_secrets.WEATHER_POSTCODE}"


def fetch_and_save() -> Path:
  """fetch Info now and save it as sim/fixtures/YYYYMMDD-HHMM.json"""
  now = datetime.datetime.now()
  print("fetching info")
  with urllib.request.urlopen(info_url(), timeout=FETCH_TIMEOUT_S) as response:
    info = json.load(response)
  FIXTURES_DIR.mkdir(exist_ok=True)
  path = FIXTURES_DIR / f"{now:%Y%m%d-%H%M}.json"
  path.write_text(json.dumps({"at": f"{now:%H:%M}", "info": info}, indent=2) + "\n")
  print(f"saved {path.relative_to(PROJECT_DIR)}")
  return path
