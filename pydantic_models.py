###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: This module provides comprehensive file validation capabilities for various input types,
# including mp3 files, Google Drive file IDs, and YouTube URLs. Utilizing Pydantic models for data
# validation and FastAPI for file uploads, it ensures that only correctly formatted and sized mp3 files,
# valid Google Drive IDs, and YouTube URLs are processed. The validators check for file extensions,
# size constraints, and adherence to specific patterns or length requirements. ExtensionChecker and
# FilenameLengthChecker classes offer additional utility methods for mp3 file validation.

# License Information: MIT License

# Copyright (c) 2024 HappyDay Johnson

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE

import os
import re
from typing import Union

from pydantic import BaseModel, field_validator, Field, ValidationError
from fastapi import UploadFile


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
