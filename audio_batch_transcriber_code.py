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
        logger.warning(f"\n---------\n {WorkflowTracker.get_model().model_dump_json(indent=4)}")
        status = WorkflowTracker.get('status')
        if status != WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name:
            # Transcribe mp3
            transcriber = AudioTranscriber()
            await transcriber.transcribe()


if __name__ == "__main__":
    asyncio.run(main())
