###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: The gdrive_helper module provides a set of tools for interacting with Google Drive.
# It offers functionalities such as authenticating with Google Drive via a service account,
# uploading and downloading files, updating file descriptions to track the status of operations,
# and handling files within specified Google Drive folders. It is designed to work closely with
# the audio_transcriber module, facilitating the management of audio files and their transcriptions
# by utilizing Google Drive's storage capabilities. This module leverages the pydrive2 library
# for Drive operations and integrates with the workflow tracking system to maintain the state
# of transcription processes.
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

from pathlib import Path
import asyncio
import json
from typing import Union

import aiofiles
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


from workflow_tracker_code import WorkflowTracker
from env_settings_code import get_settings
from logger_code import LoggerBase
from workflow_error_code import handle_error, async_error_handler
from pydantic_models import GDriveInput, TranscriptText, MP3filename




class GDriveHelper:
    """
    Facilitates interaction with Google Drive for file operations within the transcription process.

    This class provides methods to authenticate via a service account, and perform various Google Drive
    operations such as uploading, downloading, and updating file descriptions. It is designed to support
    the workflow of managing audio files and their transcriptions on Google Drive.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        gauth (GoogleAuth): Authentication object for Google Drive.
        drive (GoogleDrive): Google Drive service object for interacting with the API.
        settings (Settings): Configuration settings loaded from environment variables.
    """
    def __init__(self):
        self.settings = get_settings()
        self.logger = LoggerBase.setup_logger()
        self.gauth = self._login_with_service_account()
        self.drive = GoogleDrive(self.gauth)


    def _login_with_service_account(self):
        """
        Authenticates with Google Drive using a service account.

        This method sets up authentication for Google Drive operations by using service account credentials
        specified in the environment settings. It configures the authentication process with the necessary
        OAuth scopes and the path to the service account's JSON credentials file.

        Returns:
            GoogleAuth: An authenticated GoogleAuth instance ready for use with Google Drive operations.

        Raises:
            Exception: If authentication fails due to issues with the service account credentials or other
            related errors, the exception is propagated upwards for handling.
        """
        try:
            login_settings = {
                "client_config_backend": "service",
                "oauth_scope": self.settings.google_drive_oauth_scopes,
                "service_config": {
                    "client_json_file_path":self.settings.google_service_account_credentials_path
                }
            }
            gauth = GoogleAuth(settings=login_settings)
            gauth.ServiceAuth()
        except Exception as e:
            raise e
        return gauth

    @async_error_handler()
    async def update_mp3_gfile_status(self) -> None:
        """
        Asynchronously updates the status of the transcription process in the associated Google Drive file's description.

        Updates the file's description with the current transcription status if an MP3 file's Google Drive ID is found, and logs the workflow state.
        This ensures synchronization between the application's tracking and Google Drive.

        Decorators:
        - @async_error_handler(): Handles exceptions during the asynchronous operation.
        """
        loop = asyncio.get_running_loop()
        def _update_workflow_status():
            gfile_id = WorkflowTracker.get('mp3_gfile_id')
            if not gfile_id:
                return False
            file_to_update = self.drive.CreateFile({'id': gfile_id})
            transcription_info_json = WorkflowTracker.get_model().model_dump_json()
            # The transcription (workflow) status is placed as a json string within the gfile's description field.
            # This is not ideal, but using labels proved to be way too confusing/difficult.
            file_to_update['description'] = transcription_info_json
            file_to_update.Upload()
            return True
        # If there is no mp3 file in gdrive with the gfile_id, log an error but don't raise an exception.
        if not await loop.run_in_executor(None, _update_workflow_status):
            await handle_error(error_message='There was no mp3 gfile id in WorkflowTracker.  Status info is stored within the description field of the mp3 file.',operation='update_transcription_status_in_mp3_gfile', raise_exception=False)

    @async_error_handler()
    async def upload_mp3_to_gdrive(self, mp3_file_path:Path) -> GDriveInput:
        """
        Asynchronously uploads an MP3 file to Google Drive.

        This method uploads a local MP3 file to a specified folder in Google Drive and
        returns the Google Drive file ID of the uploaded MP3 file. The Google Drive folder
        ID is specified in the environment settings.

        Parameters:
        - input (Path): A pydantic class that verifies the mp3_file_path entry is a valid Path variable.

        Returns:
        - str: The Google Drive file ID of the uploaded MP3 file.

        Raises:
        - Exception: Propagates any exceptions raised during the uploading process to Google Drive.
        """
        folder_gdrive_id = self.settings.gdrive_mp3_folder_id
        # Returns the gfile id of the mp3 file.
        gfile_id = await self.upload_to_gdrive(GDriveInput(gdrive_id=folder_gdrive_id), mp3_file_path)
        return gfile_id

    @async_error_handler(error_message = 'Could not upload the transcript to a gflie.')
    async def upload_transcript_to_gdrive(self,  transcript_text: TranscriptText) -> None:
        """
        Asynchronously uploads a transcription text to Google Drive as a text file.

        This method generates a text file from the transcription text, naming it based on the original MP3 file's name with a '.txt' extension.
        It saves the text file locally before uploading it to the specified Google Drive folder for transcripts. The Google Drive folder is determined by environment settings.

        Parameters:
        - transcript_text (TranscriptText): The transcription text to be uploaded.

        Raises:
        - Exception with the message 'Could not upload the transcript to a gflie.' if the upload fails.

        Decorators:
        - @async_error_handler(): Handles exceptions that may occur during the upload process, providing a specific error message for upload failures.
        """
        # Use the name portion of the mp3 filename as the name portion of the transcription file.
        mp3_gfile_id = WorkflowTracker.get('mp3_gfile_id')
        mp3_gfile_input = GDriveInput(gdrive_id=mp3_gfile_id)
        mp3_filename = await self.get_filename(mp3_gfile_input)
        # Complete the transcription's filename by appending the .txt extension.
        txt_filename = mp3_filename[:-4] + '.txt'
        local_transcript_dir = Path(self.settings.local_transcript_dir)
        local_transcript_dir.mkdir(parents=True, exist_ok=True)
        local_transcript_file_path = local_transcript_dir / txt_filename
        # Save the transcript locally within the local_transcript_dir defined in the env settings.
        async with aiofiles.open(str(local_transcript_file_path), "w") as temp_file:
            await temp_file.write(str(transcript_text))
        folder_gdrive_id = self.settings.gdrive_transcripts_folder_id
        # We have a PATH variable that contains the transcript bytes.  Upload to GDrive.
        transcription_gfile_id = await self.upload_to_gdrive(GDriveInput(gdrive_id=folder_gdrive_id),local_transcript_file_path)

        return transcription_gfile_id,local_transcript_file_path

    @async_error_handler(error_message = 'Could not upload the file to GDrive.')
    async def upload_to_gdrive(self, folder_gdrive_input:GDriveInput, file_path: Path) -> GDriveInput:
        def _upload():
            folder_gdrive_id = folder_gdrive_input.gdrive_id
            gfile = self.drive.CreateFile({'parents': [{'id': folder_gdrive_id}]})
            gfile.SetContentFile(str(file_path))
            # Set the name to be the same filename as the local filename.
            gfile['title'] = file_path.name
            gfile.Upload()
            if hasattr(gfile, 'content') and gfile.content:
                gfile.content.close()
            gfile_input = GDriveInput(gdrive_id=gfile['id'])
            gfile_id = gfile_input.gdrive_id
            return gfile_id
        loop = asyncio.get_running_loop()
        gfile_id = await loop.run_in_executor(None, _upload)
        return gfile_id

    @async_error_handler(error_message = 'Could not download_from_gdrive.')
    async def download_from_gdrive(self, gdrive_input:GDriveInput, directory_path: Path):
        loop = asyncio.get_running_loop()
        def _download():
            gfile = self.drive.CreateFile({'id': gdrive_input.gdrive_id})
            gfile.FetchMetadata(fields="title")
            filename = gfile['title']
            local_file_path = directory_path / filename
            gfile.GetContentFile(str(local_file_path))
            return local_file_path

        local_file_path = await loop.run_in_executor(None, _download)
        return local_file_path

    @async_error_handler(error_message = 'Could not get the filename of the gfile.')
    async def get_filename(self, gfile_input:GDriveInput) -> str:
        gfile_id = gfile_input.gdrive_id
        loop = asyncio.get_running_loop()
        def _get_filename():
            file = self.drive.CreateFile({'id': gfile_id})
            # Fetch the filename from the metadata
            file.FetchMetadata(fields='title')
            filename = file['title']
            return filename
        filename = await loop.run_in_executor(None, _get_filename)
        verified_filename = MP3filename(filename=filename)
        return verified_filename.filename

    @async_error_handler(error_message = 'Could not fetch the transcription status from the description field of the gfile.')
    async def get_status_field(self, gdrive_input: GDriveInput) -> Union[dict, None]:
        gfile_id = gdrive_input.gdrive_id
        loop = asyncio.get_running_loop()

        def _get_status_field() -> Union[dict, None]:
            gfile = self.drive.CreateFile({'id': gfile_id})
            gfile.FetchMetadata(fields="description")

            try:
                transcription_status_json = gfile['description']
                transcription_status_dict = json.loads(transcription_status_json)
                # Update the WorkflowTracker model with the parsed dictionary
                WorkflowTracker.update(**transcription_status_dict)
            except KeyError:
                # An mp3 file just placed in the mp3 GDrive dir will not have a description field. This check creates one if this is the case.
                transcription_status_json = WorkflowTracker.get_model().model_dump_json()
                gfile['description'] = transcription_status_json
                gfile.Upload()
            # Other errors handled by the error handling decorator.
            return # WorkflowTracker is a singleton.

        await loop.run_in_executor(None, _get_status_field)
        return

    @async_error_handler(error_message = 'Could not get a list of mp3 files from the GDrive ID.')
    async def list_files_to_transcribe(self, gdrive_folder_id: str) -> list:
        loop = asyncio.get_running_loop()
        def _get_file_info():
            # Assuming get_gfile_state is properly defined as an async function
            gfiles_to_transcribe_list = []
            query = f"'{gdrive_folder_id}' in parents and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            for file in file_list:
                gfiles_to_transcribe_list.append(file)
            return gfiles_to_transcribe_list
        gfiles_to_transcribe_list = await loop.run_in_executor(None, _get_file_info)
        return gfiles_to_transcribe_list

    @async_error_handler(error_message = 'Error attempting to delete gfile.')
    async def delete_file(self, file_id: str):
        file = self.drive.CreateFile({'id': file_id})
        file.Delete()
