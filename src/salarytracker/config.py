import os
from dataclasses import dataclass

GRAPHQL_URL = "https://leetcode.com/graphql/"
BATCH_SIZE = 50
REQUEST_DELAY_SEC = 1.5
INDIA_KEYWORDS = (
    "india",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "mumbai",
    "pune",
    "noida",
    "gurgaon",
    "gurugram",
    "delhi",
    "chennai",
    "kolkata",
    "lpa",
    "inr",
    "₹",
)


@dataclass(frozen=True)
class Settings:
    llm_provider: str | None
    llm_model: str
    llm_base_url: str | None
    llm_api_key: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_base_url=os.getenv("LLM_BASE_URL"),
            llm_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"),
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key or self.llm_base_url)
