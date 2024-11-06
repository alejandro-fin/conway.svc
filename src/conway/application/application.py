import abc
from datetime                                               import datetime as _dt

from conway.application.application_config                  import ApplicationConfig
from conway.util.toml_utils                                 import TOML_Utils

class Application(abc.ABC):

    '''
    This class is supposed to be a singleton, constructed by static methods in concrete derived
    classes. Should not be constructed directly.
    It aims to group some global pluggable components that should be accessible from anywhere in code.

    :param str app_name: Name for the application. It determines the name of the configuration file. For example,
        if the application is called "Foo", the properties file would be "Foo_config.yaml"

    :param str config_path: location in the filesystem of a TOML file containing the properties
        to be used in this installation of a Conway application.

    :param Logger logger: object providing logging services that business logic can use to log messages.
        
    '''
    def __init__(self, app_name, config_path, logger):
        if not Application._singleton_app is None:
            raise RuntimeError("An attempt was made to initialize an already initialized Application, which is not allowed")
        
        self.app_name                           = app_name
        self.logger                             = logger

        PROPERTIES_FILE                         = app_name + "_config.toml"



        config_dict                             = TOML_Utils().load(config_path + "/" + PROPERTIES_FILE)
        self.config                             = ApplicationConfig(config_dict)

        # This string attribute is intended to help instrospection functionality, by recording when an application instance
        # was "born". For example, it can be used to timestamp the folders or logs associated to the lifetime of this
        # instance, to differentiate them from those of a different instance of the same application that is running
        # before or after this one.
        #
        self.start_time                         = _dt.now().strftime("%y%m%d.%H%M%S")

        Application._singleton_app              = self

    def log(self, message, log_level=1, stack_level_increase=0, xlabels=None, show_caller=True):
        self.logger.log(message, log_level, stack_level_increase, xlabels=xlabels, show_caller=show_caller)

    _singleton_app                              = None

    def app():
        if Application._singleton_app is None:
            raise RuntimeError("An attempt was made access an Application before it is initialized")

        return Application._singleton_app