
import json
from typing import List
from dotenv import load_dotenv

from pydantic_settings import BaseSettings
from pydantic import  field_validator

load_dotenv()

# Matches the variables in .env
class Settings(BaseSettings):
    gdrive_mp3_folder_id: str
    gdrive_transcripts_folder_id: str
    audio_quality_default: str
    compute_type_default: str
    google_service_account_credentials_path: str
    google_drive_oauth_scopes: List[str]
    local_mp3_dir: str
    local_transcript_dir: str

    @field_validator('google_drive_oauth_scopes')
    @classmethod
    def parse_scopes(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass  # Optionally handle error or log a warning
        return v
# Dependency that retrieves the settings
def get_settings() -> Settings:
    return Settings()