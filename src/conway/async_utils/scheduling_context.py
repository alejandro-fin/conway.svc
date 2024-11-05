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

    The purpose for snapshotting when coroutines are created is to support re-ordering logs based on the declarative
    algorithmic order, as opposed to the runtime order.

    In other words, when a coroutine log lines are created, by default they are sequenced in the order in which
    coroutines execute. That can be counter-intuitive in some situations when the logs are relied upon to easily 
    inspect the declarative algorithmic order, i.e., the sequence in which the code is written. The two orders normally
    coincide for synchronous code, but not for coroutines since they execute in non-deterministic order.

    To correct for that, the class ScheduleBasedLogSorter can take a collection of log lines and re-sort them to match
    the algorithmic order. In order to do that it relies on log lines to record information about the scheduling context,
    i.e., the call that logs must log as well the scheduling context. Such code that creates logs usually makes use of
    an instance of this class to snapshot the scheduling context information so that it can be included in the log.
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
        Returns a dictionary containing an additional labels for the Conway Logger configured to be used as part of
        the Conway application within which this code is executing.

        This additional label is for the key `TelemetryLabels.SCHEDULING_CONTEXT`, with value self.requesting_ctx

        :returns: A single-entry dictionary with key TelemetryLabels.SCHEDULING_CONTEXT, corresponding to a value
                that is a `dict` object with one entry per scheduling context property.
        '''
        return {TelemetryLabels.SCHEDULING_CONTEXT: self.ctx_dict}

    
