import sys
from types import FrameType
from typing import Any
import logging
import time


class Trace:
    def __init__(self, *filter_args):
        self.enabled = True
        self.filters = set([filter for filter in filter_args if isinstance(
            filter, str) and len(filter) > 0])

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.destroy()
        return self

    def accept(self, filename):

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

        if not self.enabled or not self.accept(filename):
            return self.trace

        self.logger.info("%s %s @ %s - %s (%s)" %
                         (event, filename, line, function, str(arguments).replace('\n', '')))

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
        self.logger = logging.getLogger('trace')
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(f'{time.strftime("%Y%m%d-%H%M%S")}_trace.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s,%(msecs)d %(message)s'))
        self.logger.addHandler(fh)
        self.logger.propagate = False

    def create(self):
        if not Trace.is_debug():            
            self.setup_log()
            sys.settrace(self.trace)

    def destroy(self):
        sys.settrace(None)
        self.logger = None
