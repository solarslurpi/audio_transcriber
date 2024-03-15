import asyncio

from gdrive_helper_code import GDriveHelper
from audio_transcriber_code import AudioTranscriber
from workflow_states_code import WorkflowEnum
from workflow_tracker_code import WorkflowTracker
from monitor_status_update import async_error_handler
from logger_code import LoggerBase
from env_settings_code import get_settings
from pydantic_models import GDriveInput

def init_WorkflowTracker_mp3(mp3_gdrive_id):
    WorkflowTracker.update(
    input_mp3 = GDriveInput(gdrive_id=mp3_gdrive_id)

    )

@async_error_handler(error_message = 'Errored attempting to manage mp3 audio file transcription.')
async def main(delete_after_upload=False):
    logger = LoggerBase.setup_logger('AudioTranscriber Manager')
    gh = GDriveHelper()
    settings = get_settings()
    folder_id = settings.gdrive_mp3_folder_id
    files_to_process = await gh.list_files_to_transcribe(folder_id)
    logger.info(f"Number of Files to process: {len(files_to_process)}")

    for file in files_to_process:
        gdrive_input = GDriveInput(gdrive_id=file['id'])
        status_model = await gh.get_status_field(gdrive_input)
        logger.warning(f"\n---------\n {status_model.model_dump_json(indent=4)}")
        if status_model.status == WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name and delete_after_upload:
            await gh.delete_file(file['id'])
        elif status_model.status != WorkflowEnum.TRANSCRIPTION_UPLOAD_COMPLETE.name:
            # Transcribe mp3
            transcriber = AudioTranscriber()
            await transcriber.transcribe()


if __name__ == "__main__":
    asyncio.run(main(delete_after_upload=False))
