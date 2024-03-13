import os
import re
from typing import Union

from pydantic import BaseModel, field_validator, Field, ValidationError
from fastapi import UploadFile

from workflow_states_code import WorkflowEnum





# Asynchronous UploadeFile validation function
async def validate_upload_file(upload_file: UploadFile):
    # Validate file extension
    valid_extensions = ['.mp3']
    _, file_extension = os.path.splitext(upload_file.filename)
    if file_extension not in valid_extensions:
        raise ValueError(f"Invalid file extension. It should be .mp3 but it is {file_extension}.")

    # Validate file size (async operation)
    await upload_file.seek(0)  # Move to end of file to get size
    file_size = len(upload_file.file.read()) # read to the end
    await upload_file.seek(0)  # Reset file pointer to beginning
    # Define your file size limit here
    min_size = 10_240  # Minimum mp3 size in bytes (10KB)
    if file_size < min_size:
        raise ValueError("File size too small to be a valid MP3 file.")
    # Return the file if all validations pass
    return upload_file

class GDriveInput(BaseModel):
    gdrive_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{25,33}$')

class ValidFileInput(BaseModel):
    input_file: Union[UploadFile, GDriveInput]



class TranscriptText(BaseModel):
    text: str

    @field_validator('text')
    @classmethod
    def text_must_be_at_least_50_characters(cls, v):
        if v is None:
            raise ValueError('Transcript text must have text.  Currently, the value is None.')
        if len(v) < 50:
            raise ValueError('Transcript text must be at least 50 characters.')
        return v

class ExtensionChecker:
    @staticmethod
    def is_mp3(filename: str) -> bool:
        """Check if the filename ends with '.mp3'."""
        return filename.endswith('.mp3')

class FilenameLengthChecker:
    MIN_LENGTH = 5  # Assuming the minimum "right length" for a filename
    MAX_LENGTH = 255  # Assuming the maximum "right length" for a filename

    @classmethod
    def is_right_length(cls, filename: str) -> bool:
        """Check if the filename's length is within the right range."""
        return cls.MIN_LENGTH <= len(filename) <= cls.MAX_LENGTH

class MP3filename(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not ExtensionChecker.is_mp3(v):
            raise ValueError("It is assumed the file is an mp3 file that ends in mp3.")
        if not FilenameLengthChecker.is_right_length(v):
            raise ValueError(f"The file length is not between {FilenameLengthChecker.MIN_LENGTH} and {FilenameLengthChecker.MAX_LENGTH} .")
        return v

class StatusModel(BaseModel):
    transcript_audio_quality: str = "medium"
    transcript_compute_type: str = "float16"
    mp3_gfile_id: str | None = None
    status: str = WorkflowEnum.NOT_STARTED.name
    comment: str | None = None
    transcript_gdrive_id: str | None = None
    transcript_gdrive_filename: str | None = None

class YouTubeUrl(BaseModel):
    yt_url: str

    @field_validator('yt_url')
    @classmethod
    def validate_youtube_url(cls, v):
        youtube_regex = re.compile(r"""
            youtube|youtu|youtube-nocookie)\.(com|be)/  # Domain
            (watch\?v=|embed/|v/|.+\?v=)?                # Path
             ([^&=%\?]{11})                               # Video ID
            """, re.VERBOSE)
        if not re.match(youtube_regex, v):
            raise ValueError('Invalid YouTube URL')
        return v

    def validate_yt_url(self, yt_url:str) -> bool:
        """
        Validates the given YouTube URL using the YouTubeUrl Pydantic model.

        Returns:
            bool: True if the URL is valid according to the YouTubeUrl model,
                False otherwise.

        This function is designed to validate URLs for UI purposes, allowing
        for user-friendly feedback without raising exceptions that would disrupt
        the UI flow.
        """
        try:
            # Validate the YouTube URL
            if YouTubeUrl(yt_url=yt_url):
                return True
        except ValidationError:
            return False
