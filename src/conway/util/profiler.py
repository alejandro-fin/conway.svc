import time

from conway.observability.logger                       import Logger
from conway.application.application                    import Application

class Profiler():
    '''
    Context manager that provides the functionality of measuring and printing the time it takes for a block of code
    to execute

    :param str behavior_being_profiled: describes the functionality that is being profiled. Used in the 
            message displayed at the end.

    '''
    def __init__(self, behavior_being_profiled):

        self.behavior_being_profiled                            = behavior_being_profiled                       


    def __enter__(self):
        '''
        Returns self after initializing internal state
        '''
        T_start = time.perf_counter()

        self.T_start                                            = T_start   
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        '''
        Prints the amount of time spent in this Profiler context manager
        '''
        T1                                                      = time.perf_counter()
        latency                                                 = "{0:.2f} sec".format(T1-self.T_start)

        # Increase stack level by 1 in the logger since this Profiler introduced an extra layer of indirection
        # between the stack frame with the business logic and the stack frame in which the logger will run. And for
        # the logger to correctly display the line of business logic code that matters, the count on stack frame
        # distances must be correct.
        Logger.log_info(f"{self.behavior_being_profiled} completed in " + latency, 
                              stack_level_increase      = 1)

        ''' TODO - figure out if we want to handle some types of exceptions
        if isinstance(exc_value, IndeExError):
            # Handle IndexError here...
            print(f"An exception occurred in your with block: {exc_type}")
            print(f"Exception message: {exc_value}")
            return True
        '''
