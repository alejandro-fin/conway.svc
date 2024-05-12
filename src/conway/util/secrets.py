from conway.application.application                 import Application
from conway.util.yaml_utils                         import YAML_Utils

class Secrets():

    '''
    Helper class containing methods to access and manipulate secrets used by a Conway-based application
    '''
    def __init__(self):
        pass

    def SECRETS_PATH():
        '''
        
        '''
        result                                  = Application.app().config.secrets_path()
        return result

    def GIT_HUB_TOKEN():
        '''
        '''
        secrets_dict                            = YAML_Utils().load(Secrets.SECRETS_PATH())
        GIT_HUB_TOKEN                           = secrets_dict['secrets']['github_token']
        return GIT_HUB_TOKEN