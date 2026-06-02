from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PUBLIC_DATA_DIR = ROOT / "public" / "data"
POSTS_FILE = DATA_DIR / "posts.jsonl"
PARSED_FILE = DATA_DIR / "parsed_posts.jsonl"
DASHBOARD_FILE = DATA_DIR / "dashboard_data.json"
PUBLIC_DASHBOARD_FILE = PUBLIC_DATA_DIR / "dashboard_data.json"

INTERVIEW_POSTS_FILE = DATA_DIR / "interview_posts.jsonl"
INTERVIEW_PARSED_FILE = DATA_DIR / "interview_parsed.jsonl"
INTERVIEW_DATA_FILE = DATA_DIR / "interview_data.json"
PUBLIC_INTERVIEW_DATA_FILE = PUBLIC_DATA_DIR / "interview_data.json"
