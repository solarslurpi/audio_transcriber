
import json

from workflow_states_code import WorkflowStates, WorkflowEnum
from workflow_error_code import async_error_handler
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker

error_state = WorkflowStates(status=WorkflowEnum.ERROR)

@async_error_handler()
async def update_status():
# state: WorkflowStates,
# comment: Optional[str] = None,
# transcript_gdrive_id: Optional[str] = None,
# store: Optional[bool] = False,
# ):
    # TODO: Validate the workflow_tracker input.  I still get confused as to why Pydantic
    # doesn't validate input attributes???
    # WorkflowStates.validate_state(state)
    logger = LoggerBase.setup_logger('update_status')

    async def _notify_status_change():
        # self.event_tracker.set()
        # await asyncio.sleep(0.1)  # Simulation of an asynchronous operation
        # self.event_tracker.clear()
        # self.logger.info(f"Status changed to {self.workflow_status.status}")
        pass

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
    # This function uses the closure for tracking status repeats
    def _update_status_repeat(state):
        # Call the counter with the current status to increment its count
        status_repeat_counter = _statusRepeatCounter()
        count = status_repeat_counter(state)
        log_message = {"state": state, "comment":WorkflowTracker.get('comment'), "count": count}
        # Log the message with the state count appended
        logger.debug(json.dumps(log_message))
    _update_status_repeat(WorkflowTracker.get('status'))
    await _notify_status_change()
