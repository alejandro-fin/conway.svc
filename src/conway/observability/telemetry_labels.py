

class TelemetryLabels:

    '''
    Class used to hold static variables for the possible telemetry labels that can be included in 
    observability signals emanated by Conway applications.

    For example, for the labels in a metric or trace.
    '''
    def __init__(self):
        pass

    '''
    Conway Log lines are initially produced as dictionaries. This string represents a field in such dictionary,
    corresponding to the root of the sub-dictionary that contains the telemetry labels of a log line.
    '''
    LABELS                                      = "labels"
    '''
    String representing the time in seconds since this Conway application started measuring time, up to
    when the observability signal was emitted. It is formatted to millisecond precision.

    Example: "0.332 sec"
    '''
    TIMESTAMP                                   = "timestamp"

    '''
    List of timestamps.
    Example: ["0.332 sec". "2.321 sec"]
    '''
    TIMESTAMP_LIST                              = "timestamp_list"

    '''
    String representing the name of the thread from which the observability signal was emitted

    Example: "MainThread"
    Example: "asyncio_2"
    '''
    THREAD                                      = "thread"

    '''
    String representing the name of the asyncio task that was running when the observability signal was emitted.
    If the signal is not emitted under the running of an event loop, then this string becomes
    "Not using an event loop".

    Example: "Task-7"
    '''
    TASK                                        = "task"

    '''
    List of task identifiers representing the ancestors of a task, sorted from parent to grand-parent to great-grandparent,
    and so on.

    Example: ["Task-6", "Task-3"]
    '''
    TASK_ANCESTORS                              = "task_ancestors"

    '''
    Instance of conway.async_utils.scheduling_context.SchedulingContext, used to reflect the moment when
    an asynchronous request was made, as opposed to the moment when it runs.

    '''
    SCHEDULING_CONTEXT                          = "scheduling_context"



    '''
    String representing the Python module and line number from which the observability signal was emitted.

    Example: "repo_manipulation_test_case:121"
    '''
    SOURCE                                      = "source"

    '''
    String for the key of the message content in the JSON object for log lines created by default by the Conway Logger.
    '''
    MESSAGE                                     = "message"

    '''
    A dict object representing the basic properties of a distributed trace's span. Time is show in seconds to a
    milliseconds precision.

    Example:

            {
                "traceId":      "1234",
                "spanId":       "loop-1",
                "parentSpanId": "papa",
                "startTime":    "2.134",
                "endTime":      "2.567",
            }

    '''
    SPAN                                        = "span"
    SPAN_TRACE_ID                               = "traceId"
    SPAN_SPAN_ID                                = "spanId"
    SPAN_PARENT_SPAN_ID                         = "parentSpandId"
    SPAN_START_TIME                             = "startTime"
    SPAN_END_TIME                               = "endTime"

