import abc
import asyncio
import inspect
import json
import os                                                       as _os
import threading
import time

from conway.application.application                             import Application
from conway.async_utils.schedule_based_log_sorter               import ScheduleBasedLogSorter
from conway.observability.telemetry_labels                      import TelemetryLabels

class Logger(abc.ABC):

    '''
    Parent class to support logging for Conway applications. Normally each concrete Conway application class
    would use a logger derived from this class, specific to that Conway application.

    :param activation_level: represents a set of binary values for which levels of logging to
        activate, where bits are machted to levels by reading the bits from right to left (i.e., the least
        significant binary digits correspond to the lowest levels of logging). 
        Examples:
        1. If `activation_level == 7`, the value corresponds to `111` in binary, which means
           that the first 3 levels of logging will be activated. 
        2. By contrast, if `activation_level == 10`, that corresponds to `1010` in binary, which means that the
           2nd and 4th levels of logging are activated (since we read bits from right to left).

        If `activation_level` is 0 then no logging occurs.
    :type activation_level: int

    :param log_file: optional parameter which is None by default. If not None, it designates the path in the local
        machine for a file where logs should be written to, in addition to getting them displayed to standard output.
    :type log_file: str

    :param schedule_based_logging: optional parameter used to enable logging based on when a line of code was
        scheduled, as opposed to when it is executed. For synchronous processing there is no difference between the
        two, but when using Python's asyncio coroutines the order in which lines is logged differs depending on whether
        log lines are sorted based on scheduling vs execution time. Refer to 
        conway.async_utils.schedule_based_log_sorter.ScheduleBasedLogSorter for a deeper discussion about this.
        One consequence of enabling schedule_based_logging is that the caller needs to periodically flush the in-memory
        buffer of the logs in order to actually get something logged. This is because schedule_based logging requires
        ScheduleBasedLogSorter to sort the buffer, and this can only happens with each flush since only then is it
        clear that the buffer is complete, i.e., it has all the lines that must be sorted.
        By default this `schedule_based_logging` parameter is False.
    :type schedule_based_logging: bool

    '''
    def __init__(self, activation_level, log_file=None, schedule_based_logging=False):

        self.activation_level                               = activation_level

        self.T0                                             = time.perf_counter()
        self.log_file                                       = log_file
        self.schedule_based_logging                         = schedule_based_logging

        # This internal buffer is only relevant when schedule_based_logging is True. Normally it is up to 
        # each concrete class to set it to True if that is the correct behavior for the use case in question.
        # This buffer will store each raw log line as an element in the list (each line represented as a JSON object), 
        # so that the entire list can be sorted later.
        #
        self.buffer                                         = []

    def log(self, message, log_level, stack_level_increase, xlabels=None, show_caller=True, flush=True):
        '''
        :param dict xlabels: optional dictionary of additional labels to attach to this log (over and beyond any generic labels
            that this Logger class will add on its own).
        :param bool show_caller: if True, causes all logs to include the filename and line number from where logging
            occurs.
        :param bool flush: optional parameter that, if True, will cause logs to be flushed out immediately (instead
            of being buffered). It is True by default.
        '''
        # Do bit-wise multiplication
        if self.activation_level & log_level > 0:

            # We want to display the module and line number for the business logic code. Normally we get here because
            # the business logic code has a line like
            #
            #       Logger.log_info(---), which in turn calls something like Application.app().log(---)
            #
            # which means we are 3 stack frames away from the business logic code, as these other layers are in between:
            #
            #   * The Application class
            #   * The concrete class derived from Application
            #   * The concrete Logger class derived from this Logger
            #
            # On top of these, the caller of the above line might have told us to further increase the stack level, 
            # if the caller felt that it was layers upstream from it whose line numbers should be displayed.
            #        
            STACK_LEVEL                                     = 3 + stack_level_increase

            labels                                          = {} if xlabels is None else xlabels.copy()

            labels                                          |= self.snapshot_runtime_context(STACK_LEVEL)

            message2                                        = self.unclutter(message)            
            self._tee(labels=labels, message = f"{message2}", filename=self.log_file)

    def flush(self):
        '''
        This method is only pertinent if self.schedule_based_logging is True. In that case, it will
        sort the buffer based on scheduling considerations, and then print it to standard output.
        '''
        if not self.schedule_based_logging:
            raise ValueError("You can't flush the buffer of a log that is configured with `schedule_based_logging=False`")
        
        sorter                                              = ScheduleBasedLogSorter(self.buffer)
        sorted_lines                                        = sorter.sort()
        print("\n") # Start on a new line
        for line in sorted_lines:
            print(line)

        # Clear buffer
        self.buffer                                         = []

    def snapshot_runtime_context(self, stack_level):
        '''
        This function inspects the state of the runtime stack, and extracts and returns useful information around:

        * The elapsed time, in seconds, it took to reach this point in the execution, measured from the time when this
          `Logger` object was constructed.
        * The thread identifier this call is running in
        * The task identifier, in the asyncio event management sense of the task
        * The line of code that triggered this execution moment, counting a number of entries up the stack based on 
          the `stack_level` parameter. I.e., if `stack_level==0` then this method will extract the caller's line number,
          but if `stack_level==1` then it will be the caller's caller's line number, and so on.

        :param stack_level: number of levels up the caller's stack to traverse in order to identify the line of code
                            that triggered this call. 
        :type stack_level: int

        :returns: The values of TelemetryLabels properties as of the time this function is called
        :rtype: dict
        '''
        T1                                                  = time.perf_counter()
        time_msg                                            = "{0:.3f} sec".format(T1-self.T0)

        thread_msg                                          = threading.current_thread().name

        try:
            task_msg                                        = asyncio.current_task().get_name()
        except RuntimeError as ex:
            if str(ex) == "no running event loop":
                task_msg                                    = "Not using an event loop"
            else:
                raise ex
      
        def _get_caller_module():
            # Add +2 to stack_level_increase to compensate for the distorting effect of having an extra stack entry 
            # due to this two functions, `snapshot_runtime_context` and `get_caller_module`
            frame                                           = inspect.stack()[stack_level + 2]
            lineno                                          = frame.lineno
            module                                          = inspect.getmodule(frame[0])
            if not module is None:
                module_name                                 = module.__name__
                source                                      = module_name.split(".")[-1] + ":" + str(lineno)
            else:
                source                                      = "<source location undetermined>"
            return source
        
        source                                              = _get_caller_module()

        TL                                                  = TelemetryLabels

        runtime_context                                     = { TL.TIMESTAMP:        time_msg,
                                                                TL.THREAD:           thread_msg,
                                                                TL.TASK:             task_msg,
                                                                TL.SOURCE:           source}
        
        return runtime_context
            

    def unclutter(self, message):
        '''
        Helper method that derived classes can use to shorten long messages. For example, replacing
        long root path names by a string for an environment variable. 
        '''
        return message

    # We use bit vectors to represent log levels

    LEVEL_DEBUG                                 = int('100', 2)
    LEVEL_DETAILED                              = int('010', 2)
    LEVEL_INFO                                  = int('001', 2)


    def log_info(msg, stack_level_increase=0, xlabels=None):
        '''
        Logs the ``msg`` at the INFO log level.

        :param str msg: Information to be logged
        :param int stack_level_increase: optional parameter, in case the caller doesn't want to appear as the
            originator if this log request. For example, setting `stack_level_increase=1` would cause the caller's caller
            to be displayed as the originator of this log line.
        :param dict xlabels: optional dictionary of additional labels to attach to this log (over and beyond any generic labels
            that this Logger class will add on its own).
        '''
        Application.app().log(msg,  Logger.LEVEL_INFO, 
                                    stack_level_increase    = stack_level_increase, 
                                    xlabels                 = xlabels,
                                    show_caller             = True) #False)

    def _tee(self, labels, message, filename=None):
        """
        NB: This implementation was contributed to by Microsoft Edge Copilot, with minor adjustments by human.
        It gives the same kind of behavior as the linux `tee` command.

        Print the message to stdout and append it to the specified file, but with a caveout:

        * The log line that is appended to the specified file is formatted as a JSON object, with Grafana-friendly
          fields like "labels". This is in order to better support integration to the Grafana stack, in the
          anticipation that some process will be scraping this file.

        * In contrast, the message that is printed to stdout will be formatted as a human-readable message with
          an informative prefix.

        Another twist is that when self.schedule_based_logging is on, we write to the given file but buffer
        the printing to standard ouput, until self.flush() is called.

        :param dict labels: labels to include in this log. They will be formatted for readability for standard output,
            but turned into a JSON object when saving to a file.
        :param str message: The message to print and append.
        :param str filename: Optional parameter for the name of the file to append to. It is ignored if set to None,
            which is the default value.
        """
        TL                                              = TelemetryLabels
        prefix                                          = f"\n[{labels[TL.TIMESTAMP]} - {labels[TL.THREAD]} - {labels[TL.TASK] } - {labels[TL.SOURCE]}]"
        if TelemetryLabels.SCHEDULING_CONTEXT in labels:
            ctx                                         = labels[TelemetryLabels.SCHEDULING_CONTEXT]
            formatted_ctx                               = f"[{ctx[TL.TIMESTAMP]} - {ctx[TL.THREAD]} - {ctx[TL.TASK] } - {ctx[TL.SOURCE]}]"
            prefix                                      += f"<<{formatted_ctx}" 

        log_entry                                   = {}
        log_entry["message"]                        = message
        log_entry["labels"]                         = labels

        if self.schedule_based_logging:
            self.buffer.append(log_entry)
        else:
            print(f"{prefix}\t{message}")  # Print to stdout

        if not filename is None:
            # Create the directory structure if it doesn't exist
            _os.makedirs(_os.path.dirname(filename), exist_ok=True)

            # We will be writing each log entry as  JSON object, each of them in a dedicated line of the log
            # file.
            # For that reason, we can't just write the dict `log_entry` as-is: it must be converted to a JSON object
            # so that field names and values use correct JSON syntax (e.g., double quotes instead of single quotes)
            #
            json_log_entry                          = json.dumps(log_entry)
            with open(filename, 'a') as file:
                file.write(f"{json_log_entry}" + '\n')  # Append to the file
