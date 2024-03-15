
import json

from workflow_error_code import async_error_handler
from logger_code import LoggerBase
from workflow_tracker_code import WorkflowTracker


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
    # This function uses the closure for tracking status repeats
    def _monitor_status_update_repeat(state):
        # Call the counter with the current status to increment its count
        status_repeat_counter = _statusRepeatCounter()
        count = status_repeat_counter(state)
        log_message = {"state": state, "comment":WorkflowTracker.get('comment'), "count": count}
        # Log the message with the state count appended
        logger.debug(json.dumps(log_message))
    _monitor_status_update_repeat(WorkflowTracker.get('status'))
