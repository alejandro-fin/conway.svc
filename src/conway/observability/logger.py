import abc
import time
import inspect
import threading
import asyncio
import os                                                       as _os

from conway.application.application                             import Application

class Logger(abc.ABC):

    '''
    Parent class to support logging for Conway applications. Normally each concrete Conway application class
    would use a logger derived from this class, specific to that Conway application.

    :param int activation_level: represents a set of binary values for which levels of logging to
        activate, where bits are machted to levels by reading the bits from right to left (i.e., the least
        significant binary digits correspond to the lowest levels of logging). 
        Examples:
        1. If `activation_level == 7`, the value corresponds to `111` in binary, which means
           that the first 3 levels of logging will be activated. 
        2. By contrast, if `activation_level == 10`, that corresponds to `1010` in binary, which means that the
           2nd and 4th levels of logging are activated (since we read bits from right to left).

        If `activation_level` is 0 then no logging occurs.

    :param str log_file: optional parameter which is None by default. If not None, it designates the path in the local
        machine for a file where logs should be written to, in addition to getting them displayed to standard output.

    '''
    def __init__(self, activation_level, log_file=None):

        self.activation_level                               = activation_level

        self.T0                                             = time.perf_counter()
        self.log_file                                       = log_file

    def log(self, message, log_level, stack_level_increase, show_caller=True, flush=True):
        '''
        :param bool show_caller: if True, causes all logs to include the filename and line number from where logging
            occurs.
        :param bool flush: optional parameter that, if True, will cause logs to be flushed out immediately (instead
            of being buffered). It is True by default.
        '''
        # Do bit-wise multiplication
        if self.activation_level & log_level > 0:
            T1                                              = time.perf_counter()
            time_msg                                        = "{0:.2f} sec".format(T1-self.T0)

            thread_msg                                      = threading.current_thread().name

            try:
                task_msg                                    = asyncio.current_task().get_name()
            except RuntimeError as ex:
                if str(ex) == "no running event loop":
                    task_msg                                    = "Not using an event loop"
                else:
                    raise ex

            # We want to display the module and line number for the business logic code. Normally we get her because
            # the business logic code has a line like
            #
            #       Application.app().log(---)
            #
            # which means we are 4 stack frames away from the business logic code, as these other layers are in between:
            #
            #   * The Application class
            #   * The concrete class derived from Application
            #   * The concrete Logger class derived from this Logger
            #   * And this Logger
            #
            # On top of these, the caller of the above line might have told us to further increase the stack level, 
            # if the caller felt that it was layers upstream from it whose line numbers should be displayed.
            #        
            STACK_LEVEL                                     = 4 + stack_level_increase
            def _get_caller_module():
                frame                                       = inspect.stack()[STACK_LEVEL]
                lineno                                      = frame.lineno
                module                                      = inspect.getmodule(frame[0])
                if not module is None:
                    module_name                             = module.__name__
                    source                                  = module_name.split(".")[-1] + ":" + str(lineno)
                else:
                    source                                  = "<source location undetermined>"
                return source
            
            source                                          = ""
            if show_caller:
                source                                      = _get_caller_module()

            message2                                        = self.unclutter(message)

            prefix                                          =f"\n[ {time_msg} - {thread_msg} - {task_msg }]\t {source} \t"
            #print(prefix + message2, flush=flush)
            self._tee(message = f"{prefix}{message2}", filename=self.log_file)

    def unclutter(self, message):
        '''
        Helper method that derived classes can use to shorten long messages. For example, replacing
        long root path names by an string for an environment variable. 
        '''
        return message

    # We use bit vectors to represent log levels

    LEVEL_DEBUG                                 = int('100', 2)
    LEVEL_DETAILED                              = int('010', 2)
    LEVEL_INFO                                  = int('001', 2)


    def log_info(msg):
        '''
        Logs the ``msg`` at the INFO log level.

        :param str msg: Information to be logged
        '''
        Application.app().log(msg, Logger.LEVEL_INFO, show_caller=False)

    def _tee(self, message, filename=None):
        """
        NB: This implementation was contributed to by Microsoft Edge Copilot, with minor adjustments by human.
        It gives the same kind of behavior as the linux `tee` command.

        Print the message to stdout and append it to the specified file.

        :param str message: The message to print and append.
        :param str filename: Optional parameter for the name of the file to append to. It is ignored if set to None,
            which is the default value.
        """
        print(message)  # Print to stdout

        if not filename is None:
            # Create the directory structure if it doesn't exist
            _os.makedirs(_os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'a') as file:
                file.write(message + '\n')  # Append to the file
