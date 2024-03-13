
import traceback
from functools import wraps

from logger_code import LoggerBase


async def handle_error(error_message: str=None, operation=None, raise_exception=True):
    logger = LoggerBase.setup_logger('handle_error')
    # Dynamically construct parts of the message based on non-None values
    parts = [
        f"Operation: {operation}" if operation else "Operation: Unknown",
        f"Error: {error_message}" if error_message else "Error: Unknown"
    ]
    err_msg = ". ".join(filter(None, parts))
    logger.error(err_msg)
    # If raise_exception is True, raise a custom exception after logging and updating the status
    if raise_exception:
        exception_message = err_msg
        raise Exception(exception_message) # pylint: disable=broad-exception-raised

def async_error_handler(error_message=None, raise_exception=True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:    # pylint: disable=broad-exception-caught
                tb_str = traceback.format_exc()
                evolved_error_message = error_message if error_message else str(e)
                detailed_error_message = f"{evolved_error_message}\nTraceback:\n{tb_str}"

                await handle_error(
                    error_message=detailed_error_message,
                    operation=func.__name__,
                    raise_exception=raise_exception
                )

                if raise_exception:
                    raise e
        return wrapper
    return decorator


# TODO: Not sure using the rest of this:
class WorkflowError(Exception):
    """Base class for errors related to workflow operations."""
    def __init__(self, message="An error occurred during workflow operation.", system_error=None):
        if system_error:
            message += f" System Error: {system_error}"
        super().__init__(message)

class WorkflowOperationError(WorkflowError):
    """Specific errors during workflow file operations."""
    def __init__(self, operation=None, detail=None, system_error=None):
        message = "A transcription operation error occurred."
        if operation:
            message = f"Failed to {operation} during transcription operation."
        if detail:
            message += f" Detail: {detail}."
        super().__init__(message, system_error=system_error)
