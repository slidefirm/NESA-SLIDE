from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

SCRIPTS_DIR = ROOT_DIR / "scripts"
DATA_DIR = ROOT_DIR / "data"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
CATALOGS_DIR = ROOT_DIR / "catalogs"
ARCHIVE_DIR = ROOT_DIR / "archive"
PROMPT_SYSTEM_DIR = ROOT_DIR / "prompt_system"

JPG_EXPORTS_DIR = DATA_DIR / "jpg_exports"
CONTACT_SHEETS_DIR = DATA_DIR / "contact_sheets"

WIREFRAMES_DIR = ARTIFACTS_DIR / "wireframes"
SVG_DIR = ARTIFACTS_DIR / "svg"
DESIGN_WEIGHT_SVG_DIR = SVG_DIR / "design"
DEPLOY_DIR = ARTIFACTS_DIR / "deploy"

LEGACY_CATALOGS_DIR = CATALOGS_DIR / "legacy"
