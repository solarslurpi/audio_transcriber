import inspect
import logging
import colorlog

# Step 1: Define the custom logging level
FLOW_LEVEL_NUM = 15
logging.addLevelName(FLOW_LEVEL_NUM, "FLOW")

def flow(self, message, *args, **kwargs):
    # Utility method for logging messages at the custom FLOW level
    if self.isEnabledFor(FLOW_LEVEL_NUM):
        self._log(FLOW_LEVEL_NUM, message, args, **kwargs) # pylint: disable=protected-access

logging.Logger.flow = flow
class CustomFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        # Get the stack frame of the caller to the logging call
        f = inspect.currentframe()
        # Go back 2 frames to find the caller
        # Adjust the range as necessary based on your logging setup
        for _ in range(10):
            f = f.f_back
        i = inspect.getframeinfo(f)

        # Add custom attributes for filename, line number, and function name to the record
        record.custom_pathname = i.filename
        record.custom_lineno = i.lineno
        record.custom_funcname = i.function

        # Now format the message with these custom attributes
        return super(CustomFormatter, self).format(record)

class LoggerBase:
    @staticmethod
    def setup_logger(name=None,level=logging.DEBUG):
        """Set up the logger with colorized output."""
        logger_name = 'TranscriptionLogger' if name is None else name
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)  # Set the logging level

        # Check if the logger already has handlers to avoid duplicate messages
        if not logger.handlers:
            # Define log format
            log_format = (
            "%(log_color)s[%(levelname)-3s]%(reset)s "
            "%(log_color)s%(custom_pathname)s:%(custom_lineno)d%(custom_funcname)s\n"
            "%(reset)s%(message_log_color)s%(message)s"
        )
            # log_format = (
            # "%(log_color)s[%(levelname)-3s]%(reset)s "
            # "%(log_color)s%(filename)s:%(lineno)d%(reset)s - "
            # "%(message_log_color)s%(message)s"
            # )
            colors = {
                'DEBUG': 'green',
                'INFO': 'yellow',
                'WARNING': 'purple',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
                'FLOW': 'cyan',  # Assign a color to the "FLOW" level
            }

            # Create a stream handler (console output)
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)  # Set the logging level for the handler

            # Apply the colorlog ColoredFormatter to the handler
            # formatter = colorlog.ColoredFormatter(log_format, log_colors=colors, reset=True,
            #                                       secondary_log_colors={'message': colors})
            formatter = CustomFormatter(log_format, log_colors=colors, reset=True,
                                        secondary_log_colors={'message': colors})

            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger
