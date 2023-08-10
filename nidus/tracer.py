import sys
from types import FrameType
from typing import Any
import logging
import time
import os


class Trace:
    def __init__(self, *filter_args):
        self.enabled = True
        self.filters = set([filter for filter in filter_args if isinstance(
            filter, str) and len(filter) > 0])
        self.logger: logging.Logger = None

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.destroy()
        return self

    def accept(self, filename: str, function: str):
        if filename.endswith("tracer.py") or function.startswith("__"):
            return False

        if len(self.filters) == 0:
            return True

        for filter in self.filters:
            if filter in filename:
                return True
        return False

    # https://stackoverflow.com/questions/5103735/better-way-to-log-method-calls-in-python
    def trace(self, frame: FrameType, event: str, arg: Any):
        filename = frame.f_code.co_filename
        line = frame.f_lineno
        function = frame.f_code.co_name
        arguments = frame.f_locals
        

        if self.enabled and self.accept(filename, function):
            arguments = str(arguments).replace('\n', '') if arguments else ""
            # arguments = ""
            self.logger.info("%s; %s; %d; %s; %s;" % (event, filename, line, function, arguments))

        return self.trace

    def is_debug():
        gettrace = getattr(sys, 'gettrace', None)

        if gettrace is None:
            return False

        v = gettrace()

        if v is None:
            return False

        return True

    def setup_log(self):
        fh = logging.FileHandler(f'{time.strftime("%Y%m%d-%H%M%S")}_{os.getpid()}_trace.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s,%(msecs)d %(message)s'))

        self.logger = logging.getLogger('trace')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        self.logger.propagate = False
        self.logger.info("event; filename; line; function; arguments;")


    def create(self):
        self.enabled = not Trace.is_debug() and int(os.getenv("TRACER_ENABLED", 1)) == 1
        if self.enabled:
            self.setup_log()
            sys.settrace(self.trace)

    def destroy(self):
        sys.settrace(None)
        self.logger = None
