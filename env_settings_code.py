###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: Defines the audio_transcriber's configuration via environment variables, utilizing
# Pydantic for robust data validation. It ensures essential settings like Google Drive
# integration details and local filesystem paths for audio and transcription files are
# properly loaded and validated. This module aids in maintaining a clear separation of
# configuration from code logic, enhancing adaptability and ease of management.
#
# Features include validation of Google Drive OAuth scopes, handling of file retention
# policies, and flexible .env file support for seamless environment-specific configurations.
#
# License Information: MIT License
#
# Copyright (c) 2024 HappyDay Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###########################################################################################

import json
from typing import List
from dotenv import load_dotenv

from pydantic_settings import BaseSettings
from pydantic import  field_validator

load_dotenv()

# Matches the variables in .env
class Settings(BaseSettings):
    """
     Configuration settings for the audio_transcriber system, loaded from environment variables.
    """
    gdrive_mp3_folder_id: str
    gdrive_transcripts_folder_id: str
    google_service_account_credentials_path: str
    google_drive_oauth_scopes: List[str]
    local_mp3_dir: str
    local_transcript_dir: str
    remove_temp_mp3: bool
    remove_temp_transcription: bool

    @field_validator('google_drive_oauth_scopes')
    @classmethod
    def parse_scopes(cls, v):
        """
        Validates and parses the 'google_drive_oauth_scopes' field from JSON string to List.

        Parameters:
            v (str): The value of 'google_drive_oauth_scopes' field from environment variables.

        Returns:
            List[str]: A list of OAuth scopes required for Google Drive access.

        Raises:
            json.JSONDecodeError: If the value cannot be decoded into a list.
        """
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass  # Optionally handle error or log a warning
        return v
# Dependency that retrieves the settings
def get_settings() -> Settings:
    """
    Loads and returns the configuration settings from environment variables.

    Returns:
        Settings: An instance of the Settings class populated with values from environment variables.
    """
    return Settings()
