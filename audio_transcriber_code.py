###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: The audio_transcriber module converts speech from audio files into
# written text. It processes audio files either uploaded directly or referenced
# by their Google Drive (gDrive) ID, producing text transcripts. The module
# utilizes Google  Drive's description field of an audio file to track the
# transcription process and uploads the resulting text to a specified Google Drive
# folder, as defined in the environment settings.
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
import asyncio
from pathlib import Path
from typing import Tuple

import aiofiles
from fastapi import UploadFile
import torch
from transformers import pipeline

from env_settings_code import get_settings
from gdrive_helper_code import GDriveHelper
from logger_code import LoggerBase
from pydantic_models import (
                             GDriveInput,
                             validate_upload_file)
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP
from workflow_error_code import async_error_handler
from status_update_code import update_and_monitor_gdrive_status

class AudioTranscriber:
    """
    Manages the transcription of audio files into text.

    This class encompasses the initial setup for the transcription environment, including configurations,
    directory paths, logging, and Google Drive helpers. It provides methods to handle the complete workflow
    of the transcription process from input to output. The workflow includes file management (both local and
    Google Drive), transcription using a specific API, and error handling throughout the process.

    Attributes:
        settings: Environmental configuration settings for the transcriber.
        logger (Logger): A logger for logging information about the transcription process.
        gh (GDriveHelper): A helper for interacting with Google Drive files.
    """
    def __init__(self):
        self.settings = get_settings()
        self.logger = LoggerBase.setup_logger("AudioTranscriber")
        self.gh = GDriveHelper()


    @async_error_handler()
    async def transcribe(self) -> str:

        """
        Transcribes audio to text, orchestrating workflow via WorkflowTracker updates.

        Prerequisites:
        - WorkflowTracker initialized with:
            - input_mp3: GDriveInput or UploadFile datatype set.
            - transcript_audio_quality: OPTIONAL. One of the text strings within
              AUDIO_QUALITY_MAP.  The default value is "default" by the WorkflowTrackerModel on instance creation.
            - transcript_compute_type: OPTIONAL. This is either "float16" or "float32".
              By default the WorkflowTrackerModel instantiates "default" ("float16").

        Workflow Progress:
        1. Validates input source and creates a local copy of the mp3 file.
        2. Uploads the mp3 file to GDrive if it isn't there already. Note: status info is
           tracked within the description field of the mp3 GDrive file.
        3. Uses Whisper to translate the audio file to text.
        4. Uploads resulting transcript to Google Drive.

        Returns:
            str: The transcribed text.

        Raises:
            -all errors are handled by the @async_error_handler() decorator.
        """
        gfile_id = None
        input_mp3 = WorkflowTracker.get('input_mp3')
        if isinstance(input_mp3, GDriveInput):
            gfile_id = input_mp3.gdrive_id
        mp3_gfile_id = gfile_id if gfile_id else None

        await update_and_monitor_gdrive_status(self.gh,status=WorkflowEnum.START.name,
        comment= "Starting the transcription workflow.", mp3_gfile_id = mp3_gfile_id)

        # First load the mp3 file (either a GDrive file or uploaded) into a local temporary file
        mp3_gfile_id, local_mp3_path = await self.create_local_mp3_from_input()

        await update_and_monitor_gdrive_status(self.gh,status = WorkflowEnum.MP3_UPLOADED.name,mp3_gfile_id = mp3_gfile_id,local_mp3_path = local_mp3_path)

        transcription_text = await self.transcribe_mp3()

        # See if we should delete the temp mp3 file based on the env setting.
        if self.settings.remove_temp_mp3:
            local_mp3_path.unlink()
            self.logger.info(f"Temporary mp3 file {local_mp3_path} deleted successfully.")
            local_mp3_path = None

        await update_and_monitor_gdrive_status(self.gh,status=WorkflowEnum.TRANSCRIPTION_COMPLETE.name,local_mp3_path=local_mp3_path, comment= f'Success! First 50 chars: {transcription_text[:50]}')

        transcript_gfile_id, local_transcript_file_path = await self.gh.upload_transcript_to_gdrive(transcription_text)

        # As with the temp mp3 file, delete the temp transcription file if requested to do so based on the env settings.
        if self.settings.remove_temp_transcription:
            local_transcript_file_path.unlink()
            self.logger.info(f"Temporary transcription file {local_transcript_file_path} deleted successfully.")
            local_transcript_file_path = None

        await update_and_monitor_gdrive_status(self.gh,status=WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name,
        transcript_gdrive_id=transcript_gfile_id,local_transcript_path= local_transcript_file_path,
        comment= 'Transcript available within the transcript folder (unless moved/deleted).')

        return transcription_text

    @async_error_handler()
    async def create_local_mp3_from_input(self) -> Path:
        """
        Asynchronously creates a local copy of an MP3 file from the specified input.

        This method handles both uploaded files and Google Drive inputs. For an uploaded file,
        it directly saves the file to a local temporary directory. For a Google Drive input,
        it downloads the file from Google Drive to the local temporary directory.

        Parameters:
        - input_file (Union[UploadFile, GDriveInput]): The source of the MP3 file, which can be
        an uploaded file (UploadFile) or a reference to a file stored in Google Drive (GDriveInput).

        Returns:
        - gfile_id: The Google Drive ID of the MP3 file.
        - Path: The path to the local copy of the MP3 file.

        Raises:
        - Exception: Propagates any exceptions raised during the file copying or downloading process.
        """
        input_mp3 = WorkflowTracker.get('input_mp3')
        if isinstance(input_mp3, UploadFile):
            # Check the contents of the UploadFile to see if it contains an mp3 file.
            await validate_upload_file(input_mp3)
            mp3_gfile_id, mp3_path = await self.copy_uploadfile_to_local_mp3(input_mp3)
        elif isinstance(input_mp3, GDriveInput):
            mp3_gfile_id, mp3_path = await self.copy_gfile_to_local_mp3(input_mp3)

        return mp3_gfile_id, mp3_path

    @async_error_handler()
    async def copy_uploadfile_to_local_mp3(self, upload_file: UploadFile) -> Tuple[str, Path]:
        """
        Asynchronously copies a FastAPI uploaded UploadFile MP3 file to a local directory and uploads it to Google Drive.

        This method takes an uploaded MP3 file, saves it to a specified local directory, and then uploads
        the file to Google Drive. It ensures the file pointer is at the start before reading, to guarantee
        accurate copying. The method wraps the file saving and uploading process with error handling.

        Parameters:
        - upload_file (UploadFile): The uploaded file object provided by FastAPI, which contains
        the MP3 file to be copied and uploaded.

        Returns:
        - Tuple[str, Path]: A tuple containing the Google Drive file ID of the uploaded MP3 file and
        the path to the local copy of the MP3 file.

        Raises:
        - Exception: Any exception raised during the file saving or uploading process is caught
        and handled by the `async_error_handler` decorator.
        """
        local_mp3_dir_path = Path(self.settings.local_mp3_dir)

        if not local_mp3_dir_path.exists():
            # All parent directories should be created if needed. Don't raise an error if the directory
            # already exists.
            local_mp3_dir_path.mkdir(parents=True, exist_ok=True)
        local_mp3_dir_path = self._make_sure_dir_exists(self.settings.local_mp3_dir)
        local_mp3_file_path = Path(local_mp3_dir_path) / upload_file.filename
        upload_file.file.seek(0)  # Rewind to the start of the file.
        async with aiofiles.open(str(local_mp3_file_path), "wb") as temp_file:
            content = await upload_file.read()
            await temp_file.write(content)
        mp3_gfile_id = await self.gh.upload_mp3_to_gdrive(local_mp3_file_path)
        return mp3_gfile_id, local_mp3_file_path


    @async_error_handler()
    async def copy_gfile_to_local_mp3(self, gdrive_input: GDriveInput) -> Tuple[str, Path]:
        """
        Downloads an MP3 file from Google Drive to the local server directory for processing.

        This function is called when the workflow starts off with a MP3 file stored on Google Drive.
        The method returns the original Google Drive ID and the local file path, aiding in file tracking
        and accessibility for the transcription process.

        Args:
            gdrive_input (GDriveInput): The pydantic class that verifies the .gdrive_ID field is a GDrive ID.

        Returns:
            Tuple[str, Path]: The Google Drive ID and the local file path where the MP3 has been saved.
        """
        local_mp3_dir_path = self._make_sure_dir_exists(self.settings.local_mp3_dir)
        local_mp3_file_path = await self.gh.download_from_gdrive(gdrive_input, local_mp3_dir_path)
        # The gdrive_id and local_file_path are returned so this workflow can be tracked.
        return gdrive_input.gdrive_id, local_mp3_file_path

    def _make_sure_dir_exists(self,dir_path):
        local_dir_path = Path(dir_path)

        if not local_dir_path.exists():
            # All parent directories should be created if needed. Don't raise an error if the directory
            # already exists.
            local_dir_path.mkdir(parents=True, exist_ok=True)
        return local_dir_path

    @async_error_handler()
    async def transcribe_mp3(self) -> str:
        """
        Transcribes a local MP3 file to text using the Whisper API based on audio quality and compute type options.
        Utilizes audio quality and compute type from `options` to tailor the transcription process.
        Updates the workflow tracker to indicate transcription start, relying on a Google Drive file ID if available.

        Args:
            options (TranscriptionOptionsWithPath): Configuration for transcription, including path to MP3 file, audio quality, and compute type.

        Returns:
            str: The transcribed text.

        Insight:
        This method is a core part of the transcription workflow, bridging between file preparation and the final text output.
        It highlights the use of specific transcription options to optimize accuracy and performance.
        """

        # Proceed with transcription using the validated options
        self.logger.debug(f"Transcribing file path: {WorkflowTracker.get('local_mp3_path')} with quality {WorkflowTracker.get('transcript_audio_quality')} and compute type {WorkflowTracker.get('transcript_compute_type')}")
        audio_quality_text_representation = WorkflowTracker.get('transcript_audio_quality')
        compute_type_text_representation = WorkflowTracker.get('transcript_compute_type')
        hf_model_name = AUDIO_QUALITY_MAP.get(audio_quality_text_representation,"default")
        compute_type_pytorch = COMPUTE_TYPE_MAP.get(compute_type_text_representation, "default")

        self.logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")

        await update_and_monitor_gdrive_status(self.gh, status=WorkflowEnum.TRANSCRIBING.name,transcript_audio_quality=hf_model_name, transcript_compute_type=compute_type_text_representation,
        comment= f'Start by loading the whisper {hf_model_name} model.')

        transcription_text = ""
        audio_file_path = WorkflowTracker.get('local_mp3_path')
        audio_file_path_str = str(audio_file_path) # Pathname to filename.
        transcription_text = await self._transcribe_pipeline(audio_file_path_str, hf_model_name, compute_type_pytorch)
        return transcription_text


    @async_error_handler()
    async def _transcribe_pipeline(self, audio_filename: str, model_name: str, compute_float_type: torch.dtype) -> str:
        """
        This method employs the Hugging Face `pipeline` for automatic speech recognition (ASR), specifying the model based on audio quality (model_name) and optimizing computation with the provided `compute_float_type`. It is designed to handle heavy lifting of audio processing in an asynchronous workflow, ensuring non-blocking operation in the main event loop.

        Args:
            audio_filename (str): The path to the audio file to be transcribed.
            model_name (str): Identifier for the Hugging Face ASR model to use.
            compute_float_type (torch.dtype): The data type for computation, indicating precision and possibly affecting performance.

        Returns:
            str: The transcribed text from the audio file.

        It's wrapped with an async error handler to gracefully handle failures, marking the transcription phase as failed in such events. The method encapsulates model loading and execution within a synchronous function, offloading it to an executor to maintain async workflow integrity.
        """
        self.logger.debug("Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL")
        def load_and_run_pipeline():
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=compute_float_type
            )
            return pipe(audio_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
        loop = asyncio.get_running_loop()
        # Run the blocking operation in an executor
        result = await loop.run_in_executor(None, load_and_run_pipeline)
        return result['text']
