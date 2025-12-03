from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = ROOT_DIR / "config.yml"
CONFIG_EXAMPLE_FILE = ROOT_DIR / "config.yml.example"

RULES_DIR = ROOT_DIR / "rules"

TEMPLATES_DIR = ROOT_DIR / "templates"