import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Instagram credentials
        self.instagram_username = os.getenv("INSTAGRAM_USERNAME", "")
        self.instagram_password = os.getenv("INSTAGRAM_PASSWORD", "")

        # OpenAI API
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        # Organization details
        self.organization_name = os.getenv(
            "ORGANIZATION_NAME", "Domestic Violence Center of Chester County"
        )
        self.helpline_number = os.getenv("HELPLINE_NUMBER", "1-800-799-7233")
        self.local_contact = os.getenv("LOCAL_CONTACT", "")

        # Content settings
        self.content_niche = os.getenv("CONTENT_NICHE", "domestic_violence_awareness")
        self.posting_interval_hours = int(os.getenv("POSTING_INTERVAL_HOURS", "1"))

        # Optional proxy
        self.proxy_url = os.getenv("PROXY_URL", None)

        # Paths
        self.base_dir = Path(__file__).parent.parent
        self.session_file = self.base_dir / "session.json"
        self.images_dir = self.base_dir / "generated_images"
        self.images_dir.mkdir(exist_ok=True)

        # Hashtags for domestic violence awareness
        self.default_hashtags = [
            "#DomesticViolenceAwareness",
            "#BreakTheSilence",
            "#SurvivorStrong",
            "#EndDomesticViolence",
            "#DVAwareness",
            "#SupportSurvivors",
            "#HealthyRelationships",
            "#YouAreNotAlone",
            "#DomesticViolence",
            "#Advocacy",
        ]

        # Content themes for rotation
        self.content_themes = [
            "awareness_statistics",
            "warning_signs",
            "support_resources",
            "survivor_empowerment",
            "healthy_relationships",
            "community_support",
            "breaking_the_cycle",
            "self_care_healing",
        ]

    def validate(self) -> list[str]:
        """Validate required settings and return list of missing ones."""
        missing = []
        if not self.instagram_username:
            missing.append("INSTAGRAM_USERNAME")
        if not self.instagram_password:
            missing.append("INSTAGRAM_PASSWORD")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        return missing
