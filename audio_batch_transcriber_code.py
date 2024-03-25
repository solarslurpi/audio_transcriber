###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: 'audio_batch_transcriber_code' automates the transcription of audio files from a
# Google Drive folder, designed for periodic execution via systemd or cron jobs. It leverages
# 'AudioTranscriber' to process untranscribed mp3 files, coordinating with helper modules for
# scanning, transcription workflow management, and uploading text transcripts back to Drive.
# This module enables efficient, automated speech-to-text conversion on a scheduled basis,
# ideal for bulk audio processing without manual oversight.

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
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###########################################################################################

import asyncio

from gdrive_helper_code import GDriveHelper
from audio_transcriber_code import AudioTranscriber
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker
from workflow_error_code import async_error_handler
from logger_code import LoggerBase
from env_settings_code import get_settings
from pydantic_models import GDriveInput

@async_error_handler(error_message = 'Errored attempting to manage mp3 audio file transcription.')
async def main():
    """
    Initiates the automated transcription process for mp3 files stored in a specified Google Drive folder.
    Utilizes the GDriveHelper to list and select files pending transcription, then processes each file through
    the AudioTranscriber. The workflow includes logging file information, managing transcription status via
    WorkflowTracker, and error handling with @async_error_handler. This function is designed for integration
    into systems that require regular, automated audio file transcription, ensuring files are transcribed
    and their statuses updated without manual intervention.

    Workflow steps:
    1. Setup logger for process monitoring.
    2. Retrieve environment settings for Google Drive folder ID.
    3. List mp3 files in the folder pending transcription.
    4. For each file, check and update transcription status.
    5. If not already transcribed, initiate transcription process.

    The process relies on environment settings for Google Drive configurations and assumes
    the presence of a structured error handling mechanism to manage potential transcription errors.
    """
    logger = LoggerBase.setup_logger('AudioTranscriber Manager')
    settings = get_settings()
    gh = GDriveHelper()
    folder_id = settings.gdrive_mp3_folder_id
    gfiles_to_process = await gh.list_files_to_transcribe(folder_id)
    logger.info(f"Number of Files to process: {len(gfiles_to_process)}")

    for g_file in gfiles_to_process:
        gdrive_input = GDriveInput(gdrive_id=g_file['id'])
        # For debug sanity check, get the name of the file.
        filename = await gh.get_filename(gdrive_input)
        logger.debug(f"mp3 filename: {filename}, gfile_id: {gdrive_input.gdrive_id}")
        await gh.sync_workflowTracker_from_gfile_description(gdrive_input)
        logger.flow(f"\n---------\n {WorkflowTracker.get_model().model_dump_json(indent=4)}")
        status = WorkflowTracker.get('status')
        if status != WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name:
            transcriber = AudioTranscriber()
            await transcriber.transcribe(input_mp3 = gdrive_input)


if __name__ == "__main__":
    asyncio.run(main())
