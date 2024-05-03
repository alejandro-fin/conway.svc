import tomllib                                         as _tomllib

class TOML_Utils():
    '''
    Utility class consisting of helper methods to manipulate TOML files.
    '''
    def __init__(self):
        pass

    def load(self, path):
        '''
        :param str path: The location of the TOML file to be loaded
        :return: the contents of the TOML file
        :rtype: dict
        '''
        try:
            with open(path, "rb") as file:
                loaded_dict                             = _tomllib.load(file)
                return loaded_dict
        except Exception as ex:
            raise ValueError("Unable to load TOML file '" + str(path) + "'. Error is:\n\t" + str(ex))
        