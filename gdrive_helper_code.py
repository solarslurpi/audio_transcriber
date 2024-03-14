from pathlib import Path
import asyncio
import json
from typing import Union

import aiofiles
from pydantic import ValidationError
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker, StatusModel
from env_settings_code import get_settings
from logger_code import LoggerBase
from update_status import async_error_handler,update_status
from workflow_error_code import handle_error
from pydantic_models import GDriveInput, TranscriptText, MP3filename




class GDriveHelper:
    def __init__(self):
        self.logger = LoggerBase.setup_logger()
        self.gauth = self._login_with_service_account()
        self.drive = GoogleDrive(self.gauth)
        self.settings = get_settings()

    def _login_with_service_account(self):
        try:
            settings = get_settings()
            login_settings = {
                "client_config_backend": "service",
                "oauth_scope": settings.google_drive_oauth_scopes,
                "service_config": {
                    "client_json_file_path":settings.google_service_account_credentials_path
                }
            }
            gauth = GoogleAuth(settings=login_settings)
            gauth.ServiceAuth()
        except Exception as e:
            raise e
        return gauth

    @async_error_handler()
    async def log_status(self) -> None:
        able_to_store_state = False
        if WorkflowTracker.get('mp3_gfile_id'):
            await self.update_transcription_status_in_mp3_gfile()
            able_to_store_state = True
        log_message = WorkflowTracker.get_model().model_dump_json(indent=4)
        state_message = f"\n-------------\nstate stored: {able_to_store_state}"
        # Combine the JSON message with the state storage status
        full_log_message = f"{log_message}\n{state_message}"
        self.logger.flow(full_log_message)

    @async_error_handler()
    async def update_transcription_status_in_mp3_gfile(self) -> bool:
        loop = asyncio.get_running_loop()
        def _update_transcription_status():
            gfile_id = WorkflowTracker.get('mp3_gfile_id')
            if not gfile_id:
                return False
            file_to_update = self.drive.CreateFile({'id': gfile_id})
            transcription_info_json = WorkflowTracker.get_model().model_dump_json()
            # The transcription (workflow) status is placed as a json string within the gfile's description field.
            # This is not ideal, but using labels proved to be way too difficult?
            file_to_update['description'] = transcription_info_json
            file_to_update.Upload()
            return True

        if not await loop.run_in_executor(None, _update_transcription_status):
            await handle_error(error_message='There was no mp3 gfile id in WorkflowTracker.  Status info is stored within the description field of the mp3 file.',operation='update_transcription_status_in_mp3_gfile', raise_exception=False)
        return True
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
        gfile_id = await self.upload(GDriveInput(gdrive_id=folder_gdrive_id), mp3_file_path)
        return gfile_id

    @async_error_handler(error_message = 'Could not upload the transcript to a gflie.')
    async def upload_transcript_to_gdrive(self,  transcript_text: TranscriptText) -> None:
        mp3_gfile_id = WorkflowTracker.get('mp3_gfile_id')
        mp3_gfile_input = GDriveInput(gdrive_id=mp3_gfile_id)
        mp3_filename = await self.get_filename(mp3_gfile_input)
        txt_filename = mp3_filename[:-4] + '.txt'
        local_transcript_dir = Path(self.settings.local_transcript_dir)
        local_transcript_file_path = local_transcript_dir / txt_filename
        async with aiofiles.open(str(local_transcript_file_path), "w") as temp_file:
            await temp_file.write(str(transcript_text))
        folder_gdrive_id = self.settings.gdrive_transcripts_folder_id

        transcription_gfile_id = await self.upload(GDriveInput(gdrive_id=folder_gdrive_id),local_transcript_file_path)
        WorkflowTracker.update(
        status=WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name,
        comment= 'Adding the transcription gfile tracker id',
        transcript_gdrive_id=transcription_gfile_id,
        transcript_filename = local_transcript_file_path.name
        )
        await update_status()
        return transcription_gfile_id,txt_filename

    @async_error_handler(error_message = 'Could not upload the transcript to gdrive transcript folder.')
    async def upload(self, folder_gdrive_input:GDriveInput, file_path: Path) -> GDriveInput:
        def _upload():
            folder_gdrive_id = folder_gdrive_input.gdrive_id
            gfile = self.drive.CreateFile({'parents': [{'id': folder_gdrive_id}]})
            gfile.SetContentFile(str(file_path))
            # Set the name to be the same filename as the local filename.
            gfile['title'] = file_path.name
            gfile.Upload()
            if hasattr(gfile, 'content') and gfile.content:
                gfile.content.close()
            #  TODO: Can remove the local transcript...
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
    async def get_status_model(self, gdrive_input: GDriveInput) -> Union[dict, None]:
        gfile_id = gdrive_input.gdrive_id
        loop = asyncio.get_running_loop()

        def _get_status_model() -> Union[dict, None]:
            gfile = self.drive.CreateFile({'id': gfile_id})
            gfile.FetchMetadata(fields="description")
            # An mp3 file just placed in the mp3 GDrive dir will not have a description field.
            # This check creates one if this is the case.
            try:
                transcription_status_json = gfile['description']
            except KeyError:
                status_model = StatusModel()
                transcription_status_json = status_model.model_dump_json()
                gfile['description'] = transcription_status_json
                gfile.Upload()

            transcription_status_dict = json.loads(transcription_status_json)
            try:
                status_model = StatusModel.model_validate(transcription_status_dict)
            except ValidationError as e:
                self.logger.error(f"{e}")
                status_model = StatusModel(status=WorkflowEnum.NOT_STARTED.name)
            return status_model

        transcription_status_dict = await loop.run_in_executor(None, _get_status_model)
        self.logger.debug(f"The transcription status dict is {transcription_status_dict} for gfile_id: {gfile_id}")
        return transcription_status_dict

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

    @async_error_handler(error_message = 'Error attempting to delete and mp3 gfile.')
    async def delete_file(self, file_id: str):
        file = self.drive.CreateFile({'id': file_id})
        file.Delete()

    @async_error_handler(error_message = 'Error attempting to delete and mp3 gfile.')
    async def reset_status_model(self, gdrive_input:GDriveInput):
        gfile_id = gdrive_input.gdrive_id
        gfile = self.drive.CreateFile({'id': gfile_id})
        status_model = StatusModel()
        status_model_json = status_model.model_dump_json()
        gfile['description'] = status_model_json
        gfile.Upload()
