import os                                                   as _os

from pathlib                                                import Path
import shutil           

class PathUtils():

    def __init__(self):
        '''
        '''

    def n_directories_up(self, file_path, n):
        '''
        Given the full path to a file, this method returns the path to a directory that is `n` levels above the file.
        For example, if `n==0` then this method returns the path to the directory that contains the file.

        As another example, that illustrates the typical use case:
        Suppose that caller is a file like 

            /home/alex/consultant1@CCL/dev/conway_fork/conway.test/src/conway_test/framework/application/chassis_test_application.py
        
        and the caller would like to retrieve the folder 

            /home/alex/consultant1@CCL/dev/conway_fork/conway.test/config

        Then the caller could call the desired folder as `PathUtils().n_directories_up(__file__, 3) + "/config"`

        :param str file_path: Absolute path to a file in the file system of the device where this code is running
        :param int n: number of directories up the `file_path` to navigate to
        :returns: the absolute path to the directory that is `n` levels above `file_path`
        :rtype: str
        '''
        directory                                       = _os.path.dirname(file_path)

        for idx in range(n):
            directory                                   = _os.path.dirname(directory)

        return directory

    def clean_path(self, path):
        '''
        Replaces characters in `path` that have a special meaning in Windows by other characters that will give the intended
        behaviour in Linux.

        In particular:

            * "\v" in Windows is interpreted as "\x0b", so to prevent this we replace "\v" by "/v"
            * "\" in Windows is interpreted as a folder separator, so we replace it by "/"
            * In the above replacements, an additional "\" is needed as an escape character

        Then returns the modified path

        :param str path: path that is to be clearned up.
        '''
        modified_path                           = path.replace("\v", "/v")          \
                                                    .replace("\\", "/")         \
                                                    .replace("//", "/")
        return modified_path
    

    def to_linux(self, path, absolute=True):
        '''
        Takes a path that might be a Windows or Linux path, and returns a linux path

        :param str path: Initial path to clean up
        :param bool absolute: Optional parameter that is True by default. If True, then the `path` is first expanded to an
                        absolute path, and the linux equivalent is returned. Otherwise, the `path` is treated as a
                        relative path and a linux equivalent relative path is returned.
        :returns: a Linux equivalent for the `path` parameter
        :rtype: str
        '''
        if absolute:
            path                                = _os.path.abspath(path)
        # The following line does not change the input if we are Linux, but will if we are Windows
        linux_path                              = path.replace("\\", "/")
        return linux_path
    
    def remove(self, path):
        '''
        Removes all contents under the absolute path ``path``. If the path does not exist, it just returns without triggering
        error messages.

        :param str path:
        '''
        if Path(path).exists():
            shutil.rmtree(path)

