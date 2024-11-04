from conway.application.application                             import Application
from conway.observability.telemetry_labels                      import TelemetryLabels

class SchedulingContext():

    '''
    Data object used to hold a snapshot of the runtime state at a point in time, such as:

    * The elapsed time since the creation of the Conway application within which this code is running

    * The thread

    * The event loop task, as when a the Python async module is used (i.e., when using coroutines)

    * The line of business logic code whose execution led to this runtime state

    Typical use case is for the code that creates coroutines, to record the time the coroutines 
    are "scheduled", i.e.,
    the moment they get added to the async event loop in Python, which is different than the later point in time when
    such coroutine runs.

    The point of recording the creation time of coroutines is that creation time corresponds to the order 
    in which lines of code are written (i.e., the algorithmic order), as opposed to the asynchronous order in which 
    lines of code are executed, which for coroutines happens later and in non-deterministic order.
    '''
    def __init__(self):

        #
        # We use stack_level=1 to accomodate for having to traverse the stack layers from the caller of
        # this method to here.
        #
        #
        self.ctx_dict                                   = Application.app().logger.snapshot_runtime_context(stack_level=1)
 

    def as_xlabel(self):
        '''
        Returns a dictionary containing an additional label for the Conway Logger configured to be used as part of
        the Conway application within which this code is executing.

        This additional label is for the key `TelemetryLabels.SCHEDULING_CONTEXT`, with value self.requesting_ctx

        :returns: A single-entry dictionary with key TelemetryLabels.SCHEDULING_CONTEXT, corresponding to a value
                that is a `dict` object with one entry per scheduling context property.
        '''
        return {TelemetryLabels.SCHEDULING_CONTEXT: self.ctx_dict}

    
