import re                                                       as _re

from conway.observability.telemetry_labels                      import TelemetryLabels

class ScheduleBasedLogSorter():

    '''
    This class embeds logic to sort log lines based on their declarative algorithmic order. This is pertinent in 
    situations when asyncio coroutines are used, given the non-deterministic order of execution.

    The above statement requires some explanation:

    By default, Conway Loggers output log lines in the order in which they are executed. For synchronous algorithms
    that order coincides with the order in which code is written, and therefore makes it possible for logs to 
    serve as a visual "trace" for the steps of an algorithm as it is executed.

    However, for asynchronous programs the log lines appear in a non-deterministic order that does not match the order
    in which the code was written, i.e., does not match the algorithmic order. That makes it hard to use logs to visually get 
    a sense for whether an algorithm's dataflow is being traversed as intended.

    To correct for that, this class provides functionality to re-sort log lines so that they appear in the order
    of the algorithm. It also formats them for readability, in the sense that log lines by default are produced
    as JSON objects with sub-JSON objects like labels, and the formatting re-expresses it in a form suitable for printing
    the the command line, with indentation as appropriate to scope portions of an algorithm subsumed under some
    calling code that schedules the coroutines in the scope in question.

    This class is stateful and each instance is intended for one-time usage, in the sense that its constructor
    takes the input lines of log to process, and the resulting instance of this class can then only sort those lines.
    If there is a need to sort another set of log lines then another instance of this class would have to be constructed.

    :param input_lines: A list of log lines as a JSON object. For example:

       ..code::

        [{  'message':  "Created 'integration' branch in 'scenario_8002.scenarios'",
            'labels':   {'scheduling_context':  {   'timestamp': '2.278 sec',
                                                    'thread': 'MainThread',
                                                    'task': 'Task-36',
                                                    'source': 'repo_manipulation_test_case:100'
                                                },
                        'timestamp':            '4.186 sec',
                        'thread':               'MainThread',
                        'task':                 'Task-38',
                        'source':               'repo_manipulation_test_case:195'}
        },

        {   'message':  "Created 'integration' branch in 'scenario_8002.docs'",
            'labels':   {'scheduling_context':  {   'timestamp': '2.288 sec',
                                                    'thread': 'MainThread',
                                                    'task': 'Task-36',
                                                    'source': 'repo_manipulation_test_case:100'
                                                },
                        'timestamp':            '4.242 sec',
                        'thread': '             MainThread',
                        'task':                 'Task-40',
                        'source':               'repo_manipulation_test_case:195'}
        }]       

    :type input_lines: list[dict]

    '''
    def __init__(self, input_lines: list[dict]):
        self.input_lines                                    = input_lines
        
        # See the documentation of `self._clean_input_lines` on why it is necessary to modify ("clean")
        # input lines to avoid serious bugs in certain situations
        self.cleaned_lines                                  = self._clean_input_lines()
        
        self.metadata_dict                                  = self._extract_task_metadata()
        

    def sort(self):
        '''
        :returns: A list of sorted and formatted log lines, indented when needed to show the parent code that scheduled
            the coroutine that led to such indented log line (i.e., "parent code" information as it appears in
            the "scheduling_context" label of the "cleaned" input log lines - as for what "cleaned" refers to,
            please see the documentation of `self._clean_input_lines`).
        
            Example: in the case of the input log cited earlier in the documentation
            of this class, the sorted output would look something like this:

            .. code::

                [2.278 sec Task-36 - MainThread@repo_manipulation_test_case:100]
                    [4.186 sec Task-38 - MainThread@repo_manipulation_test_case:195]	Created 'integration' branch in 'scenario_8002.scenarios'
                [2.288 sec Task-36 - MainThread@repo_manipulation_test_case:100]
                    [4.242 sec Task-40 - MainThread@repo_manipulation_test_case:195]	Created 'integration' branch in 'scenario_8002.docs'

            
        :retype: list[str]
        '''
        TL                                                  = TelemetryLabels
        try:
            sorted_data_l                                   = sorted(self.cleaned_lines, 
                                                                    key = lambda line: self._log_line_key(line))
        except Exception as ex:
            raise ValueError(f"Unable to sort the list of type: {type(self.cleaned_lines)}"
                             + f"\n\nREASON SORT FAILED: {ex}"
                             + f"\n\nThe input lines are: {self.cleaned_lines}")
        
        result_l                                            = []

        already_seen                                        = []
        for datum in sorted_data_l:
            
            labels                                          = datum[TL.LABELS]

            for txt in self._format_ancestors(labels):
                if not txt in already_seen:
                    result_l.append(txt)
                    already_seen.append(txt)

            msg                                             = datum[TL.MESSAGE]
            prefix                                          = self._format_labels(labels)
            # GOTCHA
            #   Application code may introduce newline characters in `msg`, as a way to format displays
            #   in multiple lines.
            #   Here we are appending a prefix to `msg`, but to preserve the spirit of the application code,
            #   we should really do it for each portion of `msg` that is separated by a newline character.
            #   Otherwise, the first line in `msg` will have a prefix but the other ones will be unindented
            #   and won't read as nice
            #
            msg_lines_l                                     = msg.split("\n")
            # Apply the prefix to the first line in `msg`, and for the others indent by the same amount of text
            result_l.append(f"{prefix}\t{msg_lines_l[0]}")
            # The indentation will be 1 space per character, except for tabs that will count as tabs
            SPACE                                           = " "
            indentation                                     = ""
            for c in f"{prefix}\t":
                if c == "\t":
                    indentation                             += c
                else:
                    indentation                             +=SPACE
            for idx in range(1, len(msg_lines_l)):
                result_l.append(f"{indentation}{msg_lines_l[idx]}")

        return result_l
    
    def _clean_input_lines(self):
        '''
        This function is required because the sorting algorithm assumes that when a log line includes a "parent"
        for a coroutine (i.e., the "scheduling_context" label of the log line, if any) is for a different 
        async task than the task of the line. When this assumption is violated, the keys for the sorting algorithm
        will be dimensionally incompatible and that will generate error messages such as this:
        
        .. code::

            TypeError: '<' not supported between instances of 'tuple' and 'float'        
        
        An example will help explain why this happens. Consider a situation where a co-routine invokes another 
        co-routine directly. This can give rise to log lines like these 2 lines, where the second line
        is for a co-routine performed under Task-24, and its parent (as per the `scheduling-context`) is another
        co-routine also for Task 24:
        
        .. code::

            {'message': '\n----------- conway.scenarios (local) -----------',
            'labels': {'timestamp': '14.185 sec',
            'thread': 'MainThread',
            'task': 'Task-12',
            'source': 'branch_lifecycle_manager:491'}}      
            
        .. code::
        
            {'message': "local = '/home/alex/consultant1@FIN/dev/conway_fork/conway.test'",
            'labels': {'scheduling_context': {'timestamp': '215.917 sec',
            'thread': 'MainThread',
            'task': 'Task-24',                                                  <<--------------
            'source': 'branch_lifecycle_manager:496'},
            'timestamp': '215.922 sec',
            'thread': 'MainThread',
            'task': 'Task-24',                                                  <<--------------
            'source': 'filesystem_repo_inspector:370'}}
  
              
        The reason this is a problem is that the sorting algorithm in this class will create 2 dimensionally
        inconsistent sorting keys, one for each line:
        
        * (14.185, 14.185)
        * ((215.911, 215.917), (215.911, 215.922))
        
        These 2 keys are dimensionally incompatible and can't be compared during a sort.
        
        To avoid generating incompatible keys like that, this function modifies the input lines by removing 
        from them any parent that is for the same task as the child, while still preserving any other ancestors.
        I.e., it has logic to "skip a level" in the hierarchy of child-parent relationships defined by the
        `scheduling_context` label, if child and parent are for the same task.
        
        In the above example, the second line would be "cleaned up" to be:
        
        .. code::
        
            {'message': "local = '/home/alex/consultant1@FIN/dev/conway_fork/conway.test'",
            'labels': {
            'timestamp': '215.922 sec',
            'thread': 'MainThread',
            'task': 'Task-24',
            'source': 'filesystem_repo_inspector:370'}}
        
        :returns: a "cleaned" verson of `self.input_lines`, as explained above
        
        :rtype: list[dict]
        '''
        TL                                                  = TelemetryLabels

        result_l                                            = []
            
        def _first_ancestor_with_a_different_task(some_labels):
            '''
            :returns: a copy of the first ancestor of `some_labels` that is for a different task. If none exists,
                returns None
                
            :rtype: dict
            '''
            task                                            = some_labels[TL.TASK]
            
            next_labels                                     = some_labels.copy()
            while TL.SCHEDULING_CONTEXT in next_labels.keys():
                next_ancestor                               = next_labels[TL.SCHEDULING_CONTEXT].copy()
                
                next_task                                   = next_ancestor[TL.TASK]

                if next_task != task:
                    # Found it!
                    return next_ancestor
                else:
                    next_labels                             = next_ancestor
                    continue
                
            # If we get this far it means that we have gone through all the ancestors and didn't find any
            # that is for a different task, so return None to indicate that no such ancestor exists
            #
            return None
            
        def _clean_labels(raw_labels):
            '''
            :returns: a modified copy of `raw_labels` which has been cleaned in the sense that the
                child-parent chain does not have the same task appearing more than once.
                
            :rtype: dict
            '''
            if not TL.SCHEDULING_CONTEXT in raw_labels.keys():
                # Hit bottom in the recursion
                return raw_labels.copy()
            else:
                # Build the clean labels by first taking the non-ancestors portion of raw_labels; later
                # we'll add the ancestor that makes most sense
                #
                cleaned_labels                              = raw_labels.copy()
                cleaned_labels.pop(TL.SCHEDULING_CONTEXT)
                
                # We will now set the `cleaned_labels`` parent by something that is clean. This means finding
                # an ancestor of `raw_labels` meeting two conditions:
                #   1. the candidate ancestor is for a different task than that of the cleaned_labels
                #   2. the candidate ancestor is itself clean
                #
                # We first ensure the 1st condition, then the 2nd condition.
                #
                first_candidate_ancestor                    = _first_ancestor_with_a_different_task(raw_labels)
                
                if first_candidate_ancestor is None:
                    # There is no valid ancestor to add to the `cleaned_labels`
                    return cleaned_labels
                
                else:
                    # Now the 2nd step: clean up the `candidate_ancestor`. For that we make a recursive call.
                    #
                    second_candidate_ancestor               = _clean_labels(first_candidate_ancestor)
                    
                    cleaned_labels[TL.SCHEDULING_CONTEXT]   = second_candidate_ancestor
                
                    return cleaned_labels
                
        for raw_line in self.input_lines:
            raw_labels                                      = raw_line[TL.LABELS]   
            cleaned_labels                                  = _clean_labels(raw_labels)
            
            cleaned_line                                    = raw_line.copy()
            cleaned_line[TL.LABELS]                         = cleaned_labels
            
            result_l.append(cleaned_line)                                       
        
        return result_l

    def _timestamp_key(ts):
        '''
        Helper method used to sort lists of timestamps, such as those produced by Conway logs, i.e., timestamps
        that are strings in the format of "11.344 sec".
        
        When used as the key for sorting, it ensures that a timestamp like "11.344 sec" appears after a timestamp 
        like "2.550 sec", and not vice-versa as it would be if the timestamps were sorted lexicographically as strings.
        
        :param ts: A timestamp produced by Conway logs, such as "2.550 sec"
        :type ts: str
        :returns: a float obtained by parsing the `ts` parameter. For example, if `ts` is "2.550 sec", then this function will return the number
            2.550
        :rtype: float
        '''
        REGEX                                           = r"(\d+.\d+) sec"
        m                                               = _re.match(REGEX, ts)
        return float(m[1])
    
    def _extract_task_metadata(self):
        '''
        Helper method that pre-processes `self.cleaned_lines` to create and return a dictionary that can be used as
        an auxiliary metadata structure.

        The returned dictionary will have the task ids as key. For example, "Task-36" could be a key.
        
        The values will be a subdictionary with two entries:
        * An entry 'timestamp_list' with values being list of timestamps (such as "2.101 sec") that appear in the log file for 
          such a task, sorted in ascending order

        * An entry 'task_ancestors' with values being a (possibly empty) list of the other tasks that are ancestors of this one, 
           sorted from immediate parent to parent's parent, and so on.
            
        The purpose of getting this list is a preliminary piece of information to correctly sort log lines, before doing a
        second pass through the log lines to actually sort thm

        An example of the dictionary returned:

        .. code::

            {
            'Task-38': {   'timestamp_list': ['2.623 sec', '3.641 sec', '4.186 sec'],
                            'task_ancestors':    ['Task-36']},
            'Task-36': {   'timestamp_list': ['2.266 sec', '2.273 sec'],
                            'task_ancestors': []},
            'Task-40': {   'timestamp_list': ['2.797 sec', '3.752 sec', '4.242 sec'],
                            'task_ancestors': ['Task-36']},
            }
        
        '''
        TL                                                  = TelemetryLabels
        ME                                                  = ScheduleBasedLogSorter
        result_dict                                         = {}

        def _extract_recursively(labels):
            '''
            Inner method so that we extrat not just the timestamp for the log line in question, but also move up the scheduling context
            hierarchy, i.e., the timestamps of prior log lines that led to this one.
            '''
            task                                            = labels[TL.TASK]
            timestamp                                       = labels[TL.TIMESTAMP]
            if not task in result_dict.keys():
                result_dict[task]                           = {TL.TIMESTAMP_LIST: [], TL.TASK_ANCESTORS: []}
            result_dict[task][TL.TIMESTAMP_LIST].append(timestamp)

            # Now make a recursive call if needed
            if TL.SCHEDULING_CONTEXT in labels.keys():
                parent_labels                               = labels[TL.SCHEDULING_CONTEXT]
                _extract_recursively(parent_labels)
                parent_task                                 = parent_labels[TL.TASK]

                parent_ancestors                            = result_dict[parent_task][TL.TASK_ANCESTORS]
                ancestors_so_far                            = result_dict[task][TL.TASK_ANCESTORS]
                ancestors                                   = list(set({parent_task}).union(set(parent_ancestors)).union(set(ancestors_so_far)))
                    
                result_dict[task][TL.TASK_ANCESTORS]        = ancestors
    

        for datum in self.cleaned_lines:
            labels = datum[TL.LABELS]
            _extract_recursively(labels)

        # Now sort and avoid duplicates
        for task in result_dict.keys():
            ts_l                                            = result_dict[task][TL.TIMESTAMP_LIST]
            # remove duplicates
            ts_l                                            = list(set(ts_l))
            # sort
            ts_l                                            = sorted(ts_l, key=ME._timestamp_key)
            result_dict[task][TL.TIMESTAMP_LIST]            = ts_l
            
        return result_dict


    def _log_line_key(self, log_line):
        '''
        Returns a sorting key to use for sorting lines created by a Conway Logger, so that the lines are re-sorted in terms 
        of the order how the code that triggers them is written, as opposed to the order in which that code is executed. 
        
        The two may differ because under asyncio, code may be written in the order in which tasks are submitted to the 
        event queue, but then executed in a different, non-determinitic order.

        They key can be a complicated "tensor" of floats representing timestamps of different events related to
        the log line or to the ancestors of the log line.

        For example, a key might be something like (12.003, 13.092) or something higher dimensional, like 
        ((3.234, 5.109), (5.503,7.950)). 

        The way to make sense of these keys is that when read left-to-right, they express a lexicographic precedence
        for which timestamps make most sense to use when sorting a log line.

        For example, consider a key like (12.003, 13.092) corresponding to a log line for an asyncio task
        "Task-5", say. Such a key says that this log line occurred at 13.092 seconds, but that an earlier log line
        for the same "Task-5" occurred at 12.003 seconds, and this earlier line was the first log line for Task-5.
        In this example, we see how we prioritize ordering first by the moment when a task first appeared, and 
        secondarily ty the moment when this log line appeared. The effect of such a policy is to cause log lines
        for the same task to be grouped together.

        Now consider a second example for a higher dimensional key like ((3.234, 5.109), (5.503,7.950)), for a
        log line for an asyncio task like "Task-12". The second pair of coordinates, (5.503,7.950), are as in
        the first example: they state that this log line appeared at moment 7.950 seconds, but that the first time
        that "Task-12" appeared was at 5.503 seconds. 
        The first pair corresponds to something else: the existence of a "parent task", such as "Task-10", 
        which run earlier and which gave rise to "Task-12". The point of having a key that gives precedence to
        parent tasks is to ensure that log lines arising from the same parent get grouped together.

        Both of these examples illustrate how our sorting key semantics ensure that outcome of sorting log
        lines in the order of algorithmic declaration, so that we list all the "children" of a "parent" together
        after the parent, making the algorithmic dataflow easy to understand because the steps of such dataflow
        would appear grouped together under the "parent" that gives rise to such dataflow.

        For this scheme to work, the dimensionality of all keys across all log lines must be the same.
        We use padding if needed.
        
        For example, if one log line has a parent and results in a key like ((3.234, 5.109), (5.503,7.950)) but another 
        log line lacks parents so it would initially result in a key like (12.003, 13.092), we apply padding to 
        the latter to turn it into ((12.003, 13.092), (0.0)) before being returned.

        Notice that this approach supports even higher dimensionalities, e.g., if a task has multiple ancestors
        and not just 1 parent, a higher dimensional "tensor" would be created as the key. The principles are analogous
        as in the examples just covered, but could result in tensors like
        (((12.003, 13.092), (0.0)), (0,0)), say, or even 
        ((((12.003, 13.092), (0.0)), (0,0)), (0,0)). 

        In all cases the key is a pair, where the 2nd member is a pair of floats, and the first pair is key of
        lower dimension.

        The padding logic requires knowledge of some information about all log lines, not just the specific
        `log_line` being processed by this function. That holistic knowledge is available through the 
        `self.metadata_dict` attribute.
    

        :param log_line: a line of log output from the Conway Logger, parsed as a JSON string that is represented as a 
            dictionary.

            Example:

            .. code::
            
                {'message':     "Created 'integration' branch in 'scenario_8002.scenarios'",
                TL.LABELS:       {   'scheduling_context': { 'timestamp':    '2.278 sec',
                                                            'thread':       'MainThread',
                                                            'task':         'Task-36',
                                                            'source':       'repo_manipulation_test_case:100'},
                                    'timestamp':    '4.186 sec',
                                    'thread':       'MainThread',
                                    'task':         'Task-38',
                                    'source':       'repo_manipulation_test_case:195'}}
                
        :type log_line: dict

        :returns: A sorting key, as a "tensor" or floats representing timestamps.

        :rtype: tuple

        '''
        TL                                                  = TelemetryLabels
        ME                                                  = ScheduleBasedLogSorter

        # We will be "padding" the keys so that they are dimensionally equal. For example, if we have a key like (12, 40) and another one
        # like ((3, 5), (5,7)), then we will pad the first key to be ((12, 40), (0,0)) so that both keys are dimensionally equal.
        # To do this, we need to compute just how much padding must be done per key. This depends on just how many ancestors line has 
        # relative to how many ancestors others lines have, i.e., the gap between a line's number of ancestors and the maximum number
        # of ancestors across all logs.
        # Hence we compute:
        #
        max_nb_ancestors                                    = max([len(self.metadata_dict[task][TL.TASK_ANCESTORS]) 
                                                                   for task in self.metadata_dict.keys()])

        
        # Labels may exist hierarchically, in the sense that a labels dict may have a "parent labels dict" in the form of the scheduling context.
        #
        # So the sorting policy is:
        #   1. For a line with multiple labels dicts, sort lexicographically starting with the labels dict highest in the hierarchy
        #   2. A labels dict A precedes a labels dict B if the first timestamp for A's task precedes the first timestamp for B's task.
        #      Here the meaning of "first timestamp" for a task is as determined by the `self.metadata_dict` attribute, i.e., the "first timestamp" for
        #      a task may be different (and earlier) than the timestamp for that task in the log line we are creating a key for.
        #
        labels                                              = log_line[TL.LABELS]

        def _labels_key(labels):
            task                                            = labels[TL.TASK]
            timestamp                                       = labels[TL.TIMESTAMP]
            if task != "Not using an event loop":
                min_timestamp                               = self.metadata_dict[task][TL.TIMESTAMP_LIST][0]
            else:
                min_timestamp                               = timestamp

            return (ME._timestamp_key(min_timestamp), ME._timestamp_key(timestamp))

        def _hierarchical_key(labels):
            
            if not TL.SCHEDULING_CONTEXT in labels.keys():
                return _labels_key(labels)
            else:
                # Find the first ancestor for a different task
                parent_labels = labels[TL.SCHEDULING_CONTEXT]

                parent_key                                  = _hierarchical_key(parent_labels)
                child_key                                   = _labels_key(labels)
                return (parent_key, child_key)
            
        def _dimension_of_key(a_key):
            '''
            Here are some examples of what we mean by dimension of a sorting key:
            
            * (2.3, 4.2) is a key of dimension 1
            
            * ((1.4, 5.2), (2.3, 4.2)) is a key of dimension 2
            
            * (((1.4, 5.2), (2.3, 4.2)), (5,6)) is a key of dimension 3
            
            :returns: the dimension of a key
            :rtype: int
            '''
            next_val                                        = a_key
            dimension                                       = 0
            while type(next_val) == tuple:
                dimension                                   += 1
                next_val                                    = next_val[0]
            return dimension

        unpadded_key                                        = _hierarchical_key(labels)
        padding_needed                                      = 1 + max_nb_ancestors - _dimension_of_key(unpadded_key)
        
        key                                                 = unpadded_key
        for idx in range(padding_needed):
            key                                             = (key, (0,0))

        return key            
    

    def _format_labels(self, labels):
        '''
        Creates and returns a nice, printable string that can be used as a prefix in a nice printout
        of a sorted log.

        As part of that, it uses tabs to indent the returned string if needed, so that nested indentation
        reflects the hierarchical relationship of a log line being for a task that is a "child" for an earlier line.

        For example, it can return an indented string such as:

        "       [4.543 sec Task-41 - MainThread@repo_manipulation_test_case:148]"

        :param metadata
        '''
        TL                                                  = TelemetryLabels
        task                                                = labels[TL.TASK]
        ts                                                  = labels[TL.TIMESTAMP]
        thread                                              = labels[TL.THREAD]
        source                                              = labels[TL.SOURCE]

        padding_needed                                      = len(self.metadata_dict[task][TL.TASK_ANCESTORS])
        padding                                             = "\t"*padding_needed

        prefix                                              = f"{padding}[{ts} {task} - {thread}@{source}]"
        return prefix

    def _format_ancestors(self, labels):
        '''
        Creates and returns a list of strings, each of then corresponding to an ancestor of the 
        task in `labels`. The string for each ancestor is a nice, printable display of a prefix for the
        labels of that ancestor.

        For example, consider this fragment of the sorted log display that this class might produce:

        [2.266 sec Task-36 - MainThread@repo_manipulation_test_case:100]
	        [2.822 sec Task-41 - MainThread@repo_manipulation_test_case:128]	Removed pre-existing repo 'scenario_8002.svc' so we can re-create it - response was null

        In this fragment, Task-36 is an ancestor of Task-41. In fact, it is the only ancestor.

        So when the labels for Task-41 are passed to this method, it will return a list of length 1 (since there
        is only 1 ancestor), like so:

        [
            "[2.266 sec Task-36 - MainThread@repo_manipulation_test_case:100]",
        ]
        '''
        TL                                                  = TelemetryLabels
        if not TL.SCHEDULING_CONTEXT in labels.keys():
            return []
        else:
            parent_labels                                   = labels[TL.SCHEDULING_CONTEXT]
            parent_formatted_ancestors                      = self._format_ancestors(parent_labels)
            formatted_ancestors                             = parent_formatted_ancestors.copy()
            formatted_ancestors.extend([self._format_labels(parent_labels)])
            return formatted_ancestors