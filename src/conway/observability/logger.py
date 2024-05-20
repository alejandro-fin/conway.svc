import abc
import time
import inspect

from conway.application.application                             import Application

class Logger(abc.ABC):

    '''
    Parent class to support logging for Conway applications. Normally each concrete Conway application class
    would use a logger derived from this class, specific to that Conway application.
    '''
    def __init__(self, activation_level):

        self.activation_level                               = activation_level

        self.T0                                             = time.perf_counter()

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

            prefix                                          ="\n[" + time_msg  + "]\t" + source + "\t"
            print(prefix + message2, flush=flush)

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
