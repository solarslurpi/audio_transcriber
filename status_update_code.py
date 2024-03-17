
import json

from workflow_error_code import async_error_handler
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker

@async_error_handler()
async def update_and_monitor_gdrive_status(gh, status, comment=None, mp3_gfile_id=None, local_mp3_path=None, transcript_audio_quality=None, transcript_compute_type=None, transcript_gdrive_id=None, local_transcript_path=None):
    """
    Asynchronously updates the transcription workflow status and monitors Google Drive (gDrive) status changes.

    This method updates the transcription workflow status in the WorkflowTracker and optionally updates the
    Google Drive file's description with the current status and comments. It is used at various stages of the
    transcription process to track progress, such as when the MP3 is uploaded, transcription starts, and
    transcription is completed. Additionally, it updates the Google Drive file's status and optionally triggers
    monitoring for status changes.

    Parameters:
    - status (str): The current status of the transcription process to be updated in the WorkflowTracker and optionally in the gDrive file's description.
    - comment (Optional[str]): Additional details about the current status, which can be appended to the gDrive file's description.
    - mp3_gfile_id (Optional[str]): The Google Drive file ID of the MP3 file. Required if updating the file's description in gDrive.
    - local_mp3_path (Optional[Path]): The local path to the MP3 file. This is tracked in the WorkflowTracker for reference but not directly used in this method.
    - transcript_audio_quality (Optional[str]): The audio quality setting used for the transcription. This is tracked in the WorkflowTracker for reference.
    - transcript_compute_type (Optional[str]): The compute type setting used for the transcription. This is tracked in the WorkflowTracker for reference.
    - transcript_gdrive_id (Optional[str]): The Google Drive file ID of the transcript file. This is tracked in the WorkflowTracker for reference.
    - local_transcript_path (Optional[str]): The filename of the transcript in Google Drive. This is tracked in the WorkflowTracker for reference.

    Raises:
    - This method is decorated with `@async_error_handler()`, which handles any exceptions that occur during its execution.

    Note:
    This method primarily updates the internal state of the workflow and optionally interacts with Google Drive to update the file's description based on the provided parameters. It leverages the `GDriveHelper` and `monitor_status_update` utilities to perform Google Drive interactions and monitoring, respectively.
    """
    # Prepare the keyword arguments for updating the WorkflowTracker
    update_kwargs = {
        'status': status,
        'comment': comment,
        'mp3_gfile_id': mp3_gfile_id,
        'local_mp3_path': local_mp3_path,
        'transcript_audio_quality': transcript_audio_quality,
        'transcript_compute_type': transcript_compute_type,
        'transcript_gdrive_id': transcript_gdrive_id,
        'local_transcript_path': local_transcript_path
    }
    # Filter out None values
    filtered_kwargs = {k: v for k, v in update_kwargs.items() if v is not None}

    # Update the WorkflowTracker
    WorkflowTracker.update(**filtered_kwargs)
    if gh and WorkflowTracker.get('mp3_gfile_id'):
        await gh.update_mp3_gfile_status()
    await monitor_status_update()

@async_error_handler()
async def monitor_status_update():
    logger = LoggerBase.setup_logger('monitor_status_update')

    def _statusRepeatCounter():
        # This dictionary will hold the count of each status update attempt
        counts = {}
        # closure to maintain the counts.
        def counter(status):
            # Increment the count for the given status
            if status in counts:
                counts[status] += 1
            else:
                counts[status] = 1
            # Optionally, you can return the current count for the given status
            return counts[status]

        return counter

    def _monitor_status_update_repeat(state):
        # Call the counter with the current status to increment its count
        status_repeat_counter = _statusRepeatCounter()
        count = status_repeat_counter(state)
        log_message = {"state": state, "comment":WorkflowTracker.get('comment'), "count": count}
        # Log the message with the state count appended
        logger.debug(json.dumps(log_message))
    _monitor_status_update_repeat(WorkflowTracker.get('status'))
