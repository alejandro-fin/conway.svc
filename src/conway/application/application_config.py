import os                                                   as _os

class ApplicationConfig():

    '''
    Class encapsulating the configuration of a Conway-based application

    :param dict config_dict: contains the names and values of properties, as a hierarchical dictionary
    '''
    def __init__(self, config_dict):
        self.config_dict                                    = config_dict


    def secrets_path(self):
        '''
        Provides the location of a "secrets.yaml" file containing the secrets needed by a Conway-based application

        :return: location of "secrets.yaml"
        :rtype: str
        '''
        result                                              = self.config_dict['secrets']['vault_location']

        # Evaluate any environment variables in the path
        #
        result                                              = _os.path.expandvars(result) 

        return result