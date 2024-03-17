from enum import Enum

from difflib import get_close_matches
from pathlib import Path
from typing import Optional, Union

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

import torch

from pydantic import BaseModel, field_validator, field_serializer

from logger_code import LoggerBase
from pydantic_models import GDriveInput

AUDIO_QUALITY_MAP = {
    "default":  "distil-whisper/distil-large-v2",
    "tiny": "openai/whisper-tiny",
    "tiny.en": "openai/whisper-tiny.en",
    "base": "openai/whisper-base",
    "base.en": "openai/whisper-base.en",
    "small": "openai/whisper-small",
    "small.en": "openai/whisper-small.en",
    "medium": "openai/whisper-medium",
    "medium.en": "openai/whisper-medium.en",
    "large": "openai/whisper-large",
    "large-v2": "openai/whisper-large-v2",
    "distil-large-v2": "distil-whisper/distil-large-v2",
    "distil-medium.en": "distil-whisper/distil-medium.en",
    "distil-small.en": "distil-whisper/distil-small.en",

}

COMPUTE_TYPE_MAP = {
    "default": torch.float16,
    "float16": torch.float16,
    "float32": torch.float32,
}


class WorkflowTrackerModel(BaseModel):
    transcript_audio_quality: str = "default"
    transcript_compute_type: str = "default"
    input_mp3: Optional[Union[UploadFile, GDriveInput]] = None
    mp3_gfile_id: Optional[str] = None
    local_mp3_path: Union[Path, None] = None
    status: str = None
    comment: Optional[str] = None
    transcript_gdrive_id: str = None
    local_transcript_path: str = None

    @field_serializer('input_mp3',when_used='json-unless-none')
    def serialize_input_mp3(self,input_mp3):
        if isinstance(input_mp3,UploadFile):
            file_info = jsonable_encoder(input_mp3)
        elif isinstance(input_mp3, GDriveInput):
            file_info = input_mp3.gdrive_id
        else:
            raise ValueError(" The input_mp3 was neither of type GDriveInput or UploadFile.")
        return file_info


    @field_validator('transcript_audio_quality')
    @classmethod
    def check_audio_quality(cls, v):
        if v not in AUDIO_QUALITY_MAP:
            raise ValueError(f"{v} is not a valid audio quality.")
        return v

    @field_validator('transcript_compute_type')
    @classmethod
    def check_compute_type(cls, v):
        if v not in COMPUTE_TYPE_MAP:
            raise ValueError(f"{v} is not a valid compute type.")
        return v

    @field_serializer('local_mp3_path')
    def serialize_local_mp3_path(self, local_mp3_path: Path):
        if local_mp3_path:
            return str(local_mp3_path.name)
        return None

    @field_validator("local_mp3_path")
    @classmethod
    def validate_local_mp3_path(cls, v: Union[str, Path, None]) -> Path:
        """
        Validates the local_mp3_path field to be:
            - None
            - A valid Path object (absolute or relative)
            - Not pointing to a non-existent file or is not a file.
            - The file contains at least minimal bytes for an mp3 file (rough estimate)
        """
        if v is None:
            return None

        if not isinstance(v, Path):
            raise ValueError("local_mp3_path must be a Path object or None")

        if not v.exists():
            raise ValueError(f"Path: '{v}' does not exist")

        # Check file size (adjust max_file_size as needed)
        min_mp3_file_size = 1_024
        if v.is_file() and v.stat().st_size < min_mp3_file_size:
            raise ValueError(f"Audio file is not large enough to contain an mp3 file. The filesize is {min_mp3_file_size} bytes.")

        return v


class WorkflowTracker:
    _model = WorkflowTrackerModel()
    _logger = LoggerBase.setup_logger('WorkflowTracker')

    @classmethod
    def update(cls, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, Enum):
                # Assuming you want to use the first value in the tuple for the enum
                actual_value = value.value[0]  # Adjust this as needed
            else:
                actual_value = value
            if hasattr(cls._model, key):
                setattr(cls._model, key, actual_value)
            else:
                real_field_name = cls.get_similar_field_name(key)
                if real_field_name:
                    setattr(cls._model, real_field_name, actual_value)
                    cls._logger.info(f"Updated similar field name: {real_field_name} for entered key: {key}")
                else:
                    raise ValueError(f"{key} is not a property of WorkflowTrackerModel and no similar field found.")


    @classmethod
    def get(cls, field_name):
        if hasattr(cls._model, field_name):
            return getattr(cls._model, field_name, None)
        else:
            real_field_name = cls.get_similar_field_name(field_name)
            if real_field_name:
                cls._logger.info(f"Entered field name: {field_name}. Returning similar WorkflowTrackerModel property: {real_field_name}")
                return getattr(cls._model, real_field_name, None)
            else:
                raise ValueError(f"{field_name} is not a property of WorkflowTrackerModel and no similar field found.")

    @classmethod
    def get_similar_field_name(cls, input_name, cut_off=0.6) -> Optional[str]:
        """
        Retrieves the most similar field name based on the input name.

        Parameters:
        - input_name: The name to find a match for.
        - model_fields: A list of field names to match against.
        - cutoff: The similarity threshold; names with a similarity score above this will be considered. Range [0, 1].

        Returns:
        - The most similar field name if a match is found, otherwise None.
        """
        model_fields = list(WorkflowTrackerModel.model_fields.keys())
        matches = get_close_matches(input_name, model_fields, n=1, cutoff=cut_off)
        if matches:
            cls._logger.debug(f"The input name from the caller {input_name} was not a field name of the WorkflowTrackerModel. Returning the WorkflowTrackerModel field name {matches[0]}")
        return matches[0] if matches else None


    @classmethod
    def __call__(cls, **kwargs):
        cls.update(**kwargs)
        return cls._model

    @classmethod
    def get_model(cls):
        return cls._model
