import warnings
import traceback
from io                                                 import StringIO

from conway.util.path_utils                             import PathUtils

class ConwayWarningMessage(warnings.WarningMessage):
    '''
    Helper data structure used by WarningFilter. It extends the parent class with additional stack trace
    information that Conway is interested in providing to the developer, so that the developer know 
    where the warnings are being raised from and cleans them up.

    :param str stacktrace: represents the stack trace from which a warning was raised
    '''
    def __init__(self, message, stacktrace, category, filename, lineno, file=None, line=None, source=None):
        super().__init__(message, category, filename, lineno, file, line, source)

        self.stacktrace             = stacktrace

class WarningsFilter():
    '''
    Context manager to implement a policy whereby a Conway-based application should never issue warnings,
    and alerts the user if any such warning corresponds to a user error.

    The motivation for this policy is prevent sloppy behavior by developers whereby they allow their application
    to emit a lot of spurious warnings and never clean them up.

    To prevent that, the WarningsFilter context manager requires that developers explicity declare the kind
    of warnings that are benign. Any other type of warning is treated as an error and for that reason this
    WarningsFilter would raise either a RuntimeError or a ValueError, depending on whether the fault
    lies with the Conway application codebase (i.e., a "bug" or malfunction, hence a RuntimeError)
    or with the user (a ValueError).

    A typical example of a benign warning is a DeprecationWarning in a 3rd party library. Such warning is
    intended for the developers of the 3rd party library, not the developers of a Conway-based application. 
    Therefore, Conway application developers can register such benign warnings with this WarningsFilter
    so that they are suppressed. That stops the Conway-based application from logging spurious messages.

    A second use case for this context manager
    is that some warnings from 3rd-party libraries are really the result of user errors.
    In those cases we want to guide the user for how to correct the error. First of all, we want to make 
    the user aware that an error happened in the first place: i.e., the warning should be turned into an
    exception, not just a message lost in a big log that nobody looks at. 
    Second, we want to provide a user-friendly message in terms of the domain model of the
    Conway application that the user understands, not the obstruse inner workings of a 3rd-party library
    used within the Conway application

    To address the above use cases, this context manager will accumulate warnings silently during its processing.
    Then upon exiting the WarningsFilter will look at the warnings. If any is for a user error, it will
    raise a ValueError for the first such warning it encounters.

    If no warning is a user error, but if there are warnings that were not previously registered as benign,
    then this WarningsFilter will collect them into a single message and raise a RuntimeError. This RuntimeError
    is intended to notify the Conway application developer that they probably have a "bug". This might
    be as simple as needing to register additional benign warnings, or 
    possibly fix something more serious in the code.

    To assist the Conway application developer in this task, the RuntimeError raised by this WarningsFilter
    will include information for each non-benign warning, including the stack trace in the Conway application
    that led to the warning. 

    '''
    def __init__(self):
        '''
        '''  
        # Internally, we delegate to the standard Python context manager for warnings, which suppress warning messages 
        # while the context manager is active and (if record=True) will accumulate those warnings in a list
        #
        self.ctx                                                = warnings.catch_warnings(record=True)

        # This list will be populated in the self.__enter__() method. The list will contain objects
        # of type ConwayWarningMessage.
        #
        self.warnings_l                                         = None


    def __enter__(self):
        '''
        Returns self after initializing internal state
        '''
        # We want that the Python warnings module emits warnings that include the stack trace information.
        # For that reason we want it to emit ConwayWarningMessage objects.
        #
        # This implementation is inspired by https://stackoverflow.com/questions/22373927/get-traceback-of-warnings
        # which shows that we can accomplish this by setting the Python warnings module's 
        # `showwarning` property to be a Conway-specific function

        def _warn_with_traceback(message, category, filename, lineno, file=None, line=None):

            log                                                 = StringIO()
            traceback.print_stack(file=log)
            log.write(warnings.formatwarning(message, category, filename, lineno, line))
            stacktrace                                          = log.getvalue()
            warn_msg                                            = ConwayWarningMessage(message, 
                                                                                       stacktrace, 
                                                                                       category, 
                                                                                       filename, 
                                                                                       lineno, 
                                                                                       file, 
                                                                                       line)
            self.warnings_l.append(warn_msg)

        self.warnings_l                                         = self.ctx.__enter__()

        warnings.showwarning                                    = _warn_with_traceback

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        '''
        Examines the warnings that have been accumulated throughout the life of this WarningsFilter
        context manager, and ignores any that are registered as benign with this WarningsFilter.

        For the rest, it checks if any corresponds to a user error. If so, it raises a ValueError
        at the first one encountered.

        If not is a user error, then the non-benign warnings are aggregated and a single RuntimeError
        is raised whose message contains the information about all the non-benign warnings.
        '''

        # First some housekeeping: exit the nested context manager to restore the state of the Python
        # warnings module, i.e., stop capturing warnings instead of logging them out.
        #
        self.ctx.__exit__(exc_type, exc_value, exc_tb)

        # Now examine the warnings we have collected
        #
        if len(self.warnings_l) > 0:
            bad_warnings_dict                                   = {} # One entry per bad warning; value is a dict
            bad_warning_counter                                 = 0
            for idx in range(len(self.warnings_l)):
                a_warning                                       = self.warnings_l[idx]
                self.check_if_user_error(a_warning)
                if self.check_if_should_ignore(a_warning):
                    # In this case, this particular warning should not trigger an error.
                    # So ignore it and move on to examining the next warning
                    continue

                # If we get this far, then we have a non benign warning
                #
                a_warning_dict                                  = {} # Will hold information about 1 single problematic warning

                PREFIX                                          = f"[WARNING {bad_warning_counter}]"
                DASHES                                          = "."*40

                a_warning_dict[f"{PREFIX} Category: "]          = str(a_warning.category)
                a_warning_dict[f"{PREFIX} Message: "]           = str(a_warning.message)
                a_warning_dict[f"{PREFIX} ... from:"]           = PathUtils().to_linux(str(a_warning.filename))
                a_warning_dict[f"{PREFIX} ... at line:"]        = str(a_warning.lineno)

                trace_msg                                       = f"\n{DASHES} {PREFIX} Stack trace begins {DASHES}\n\n"
                trace_msg                                       += f"{a_warning.stacktrace}"
                trace_msg                                       += f"\n{DASHES} {PREFIX} Stack trace ended {DASHES}\n\n"
                a_warning_dict[f"{PREFIX} Stack trace that triggered warning:"]  = trace_msg

                bad_warning_counter                             += 1
                bad_warnings_dict[bad_warning_counter]          = a_warning_dict

            nb_bad_warnings                                     = len(bad_warnings_dict.keys())

            if nb_bad_warnings > 0:
                
                for idx in bad_warnings_dict.keys():
                    a_warning_dict                              = bad_warnings_dict[idx]
                    aggregate_msg                               = ""
                    for k in a_warning_dict.keys():
                        val                                     = a_warning_dict[k]
                        aggregate_msg                           += f"\n{k}\t{val}"
                    raise RuntimeError(f"Encountered {nb_bad_warnings} non-benign  warning(s)"
                                    + f"\nDetails: {aggregate_msg}")


    def check_if_user_error(self, a_warning):
        '''
        Helper method for this class to handle certain warnings that a Conway application considers user errors, as
        opposed to development-type errors.

        Normally 3rd-party warnings should be pre-empted at development time by the Conway application developers
        using those 3rd party dependencies correctly, avoiding code constructs that the 3rd party flags as
        risky or deprecated.

        However, in some cases the warning from the 3rd party library is really a user error, so the
        remedy lies with the user.
         
        In those cases, we want to assist the user with useful information about how to correct the error.
        It is often not a good idea to just cascade the warning message to the user "as is", since
        the warning typically has jargon related to the 3rd party
        library that the user knows nothing about. So to improve usability, this method allows Conway application
        developers to convert such obstruse warnings into a ValueError whose message is expressed in terms of
        the Conway application domain model, which is what the user can understand. The ValueErorr is raised
        by this message.

        :param ConwayWarning a_warning: a warning for which we want to determine if it corresponds to a user
            error.
    
        '''

        # Here is a sample implementation for this method. In this example, a Conway application has made
        # a design decision that some Pandas warnings are really end-user errors. So they are caught
        # and converted to a friendly error message. In case it is needed, the original message and stack
        # trace from the warning are also included in the error message. Additionally, the developer
        # put comments in the code to indicate the reasoning for why such warning should be interpreted 
        # as a user error.
        #
        '''
        if str(a_warning.message).startswith("Defining usecols with out of bounds indices is deprecated"):
            # This is Pandas warning that happens when the user submits an Excel posting with a range of
            # columns that includes blank columns. For example, the user might submit H2:L30 as a range,
            # but if column L is blank, then the user should instead have submitted H2:K30
            #
            warning_dict        = {"Problem encountered": a_warning.message}
            raise ValueError("Something went wrong, most probably because you might be attempting "
                                + "to post an Excel file and one of the PostingLabel's ranges includes empty "
                                + "Excel columns. If so, please correct your PostingLabel and try again."
                                + f"\nProblem encountered: {a_warning.message}"
                                + f"\nStack trace: {a_warning.stack_trace}")

        else:
            pass
        '''

    def check_if_should_ignore(self, a_warning):
        '''
        Helper method for this class to handle certain warnings from 3rd party libraries that Conway should ignore.
        
        :returns: True if the warning should be ignored, and False otherwise
        :rtype: bool
        '''
        # Here is an example implementation for this method, where the Conway application developer has
        # decided that a couple of warnings are benign.
        # The example illustrates a good practice: document for each benign warning the reasoning for why
        # it is considered benign.
        #
        '''
        if a_warning.category == ResourceWarning and str(a_warning.message).startswith("unclosed event loop"):
            #Ignore such warnings - they are noise generated by YAML
            return True

        elif a_warning.category == DeprecationWarning and str(a_warning.message).startswith("getargs: The 'u' format is deprecated. Use 'U' instead"):
            #   This started being thrown in Python 3.10.x on Windows platforms (at least since 3.10.4)
            #   In the application code base, this came up in the test case
            #           util.tests_unit.test_formatting_utils.Test_NotebookUtils.test_notebook_run
            #
            #   It causes warnings like these:
            #        File "<PYTHON MODULE>/pywintypes.py", line <HIDDEN>, in __import_pywin32_system_module__
            #            found = _win32sysloader.LoadModule(filename)
            #        <PYTHON MODULE>/pywintypes.py:65: DeprecationWarning: getargs: The 'u' format is deprecated. Use 'U' instead.
            #    
            return True       
        else:
            return False
        '''
        source                                      = PathUtils().to_linux(str(a_warning.filename))
        category                                    = a_warning.category
        message                                     = a_warning.message

        BENIGN_WARNING_1                            = "datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version"
        BENIGN_SOURCES_1                            = ["site-packages/xlsxwriter", "site-packages/openpyxl"]
        SOURCE_IS_BENIGN_1                          = len([elt for elt in BENIGN_SOURCES_1 if elt in source]) > 0
        
        if category == DeprecationWarning and str(message).startswith(BENIGN_WARNING_1) and SOURCE_IS_BENIGN_1:
            #   This started when we upgraded to the 3rd-party module xlsxwriter v 3.1.1.
            #   Looks like it is just a matter for the authors of xlsxwriter to change their code to use the correct
            #   datetime method. Until they do that, we treat this warning as benign and ignore it.
            #   For reference, this is an extract of how this warning would appear in TVM test cases if it is not suppressed:
            #
            #        [WARNING 85] Category:  <class 'DeprecationWarning'>
            #        [WARNING 85] Message:   datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
            #        [WARNING 85] ... from:  /home/alex/miniconda3/envs/tvm-env/lib/python3.12/site-packages/xlsxwriter/core.py
            #        [WARNING 85] ... at line:       138
            #               
            #    
            return True       
        else:
            # Treat the warning non-benign - so this will trigger an exception so that the developer figures out how
            # to clean the code so that such warning is not issued
            #
            return False


