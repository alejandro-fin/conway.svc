import abc
from pathlib                                                                    import Path

from conway.database.data_hub                                      import DataHub
from conway.database.data_accessor                                 import DataAccessor

class DataHubHandle(abc.ABC):

    '''
    Helper class to abstract away the two possible ways of representing the root folder of a SingleRootDataHub
    '''
    def __init__(self):
        pass

    @abc.abstractmethod
    def hub_root(self):
        '''
        '''
    @abc.abstractmethod
    def snapshot_handle(self, snapshot_root_folder: str):
        '''
        :return: A new object of the same class as this instance, but with the root folder changed to be
            the given ``snapshot_root_folder``
        :rtype: DataHubHandle
        '''

class RelativeDataHubHandle(DataHubHandle):

    '''
    '''
    def __init__(self, db_root_folder, relative_path):
        super().__init__()
        self.db_root_folder                     = db_root_folder
        self.relative_path                      = relative_path

    def hub_root(self):
        '''
        '''
        return self.db_root_folder + "/" + self.relative_path
    
    def snapshot_handle(self, snapshot_root_folder: str):
        return RelativeDataHubHandle(snapshot_root_folder, self.relative_path)

class AbsoluteDataHubHandle(DataHubHandle):

    '''
    '''
    def __init__(self, hub_root_folder):
        super().__init__()
        self.hub_root_folder                    = hub_root_folder

    def hub_root(self):
        '''
        '''
        return self.hub_root_folder
    
    def snapshot_handle(self, snapshot_root_folder:str):
        return AbsoluteDataHubHandle(snapshot_root_folder)
    
class GitHubDataHubHandle(DataHubHandle):

    '''
    Handle to a DataHub that corresponds to a related collection of repos in GitHub.

    :profile conway_ops.onboarding.user_profile.UserProfile profile: object representing a loaded configuration for
        a user's profile. The profile would determine which GitHub repos and credentials are part of this DataHub.
    '''
    def __init__(self, profile):
        super().__init__()
        self.profile                    = profile

    def hub_root(self):
        '''
        '''
        return self.profile.REMOTE_ROOT
    
    def snapshot_handle(self, snapshot_root_folder:str):
        # Since the DataHub is in a remote cloud (GitHub), there is no point of "snapshotting" it into a 
        # separate `snapshot_root_folder` -i.e., there is no "seed" that needs to be copied to an "actual" environment
        return self



class SingleRootDataHub(DataHub, abc.ABC):

    def __init__(self, name, hub_handle: DataHubHandle):
        '''
        Class that provides the most common case for a DataHub: content that is rooted at a single directory
        in the file system.

        The root directory is encapsulated by the :class:`DataHubRoot` hierarchy, to support different ways how
        the DataHub's root may be expressed:

        * As an absolute path

        * Or as a combination of the absolute path to some containing database, followed by a relative path from
          there to the folder containing the DataHug

        :param DataHubHandle hub_handle: Handle to the folder under which this DataHub resides.
        '''
        super().__init__(name = name)

        if not isinstance(hub_handle, DataHubHandle):
            raise ValueError("Expected a DataHubHandle, but got a '" + str(type(hub_handle)) + "' instead.")
        self.hub_handle                                     = hub_handle

    def hub_root(self):
        '''
        '''
        return self.hub_handle.hub_root()

    def populate_from_seed(self, seed_hub):
        '''
        @param seed_hub A SingleRootDataHub object. This method will wipe out any pre-existing contents of self and
                initialize it to be a copy of what is inside the `seed_hub`
        '''
        # First, remove pre-existing content, if any
        #
        with DataAccessor(self.hub_root()) as ax:
            ax.remove()

        # Now copy the data from the seed
        #
        self.enrich_from_seed(seed_hub)
        
    def enrich_from_seed(self, seed_hub):
        '''
        @param seed_hub A SingleRootDataHub object. This method will enrich the contents of self by adding
            additional content from the `seed_hub`. If the new content has the same filename as pre-existing
            content, then the pre-existing content is overwritten.
        '''
        # Copy the data from the seed
        #
        with DataAccessor(url = self.hub_root()) as ax:
            ax.copy_from(src_url=seed_hub.hub_root())
        
    def create_snapshot(self, snapshot_root_folder):
        '''
        This method creates a copy of this DataHub content and saves it to a folder whose name is given by the
        `snapshot_name` parameter. 

        A main use case for this notion of "snapshot" is the test harness: some tests need to exercise the business
        logic over multiple time periods, and in the process may want to save a copy of what a DataHub's content
        is at various points along the way. 

        Here is an example for such a use case, identified as scenario 1001. Suppose this method is called on an 
        DataHub object representing content under a root like

            ".../vulnerability_management_scenarios/1001/ACTUALS@latest/publications"

        In our use case, the test case might want to do multiple snapshots that can be thought of as "ACTUALS@T1", "ACTUALS@T2", 
        "ACTUALS@T3", etc. for what the database looked at various points in the test's dataflow, such as at times T1, T2, T3, ... 

        The parameter `snapshot_root_folder` should be given in accordance with that intention. For example, if the intention
        is to snapshot data as of time T2, the natural value for the `snapshot_root_folder` parameter would be 

            ".../vulnerability_management_scenarios/1001/ACTUALS@T2/publications"


        @param snapshot_root_folder A string that identifies the full path to the snapshot
        '''
        # First, remove pre-existing content, if any
        #
        snapshot_handle                                     = self.hub_handle.snapshot_handle(snapshot_root_folder)
        with DataAccessor(snapshot_handle.hub_root()) as ax:
            ax.remove()

        # Now copy the data from the seed
        #
        snapshot_hub                                            = self._instantiate(name        = self.name,
                                                                                    hub_handle  = snapshot_handle)
        snapshot_hub.enrich_from_seed(self)

    @abc.abstractmethod
    def _instantiate(self, name: str, hub_handle: DataHubHandle):
        '''
        Returns an instance of this concrete DataHub class

        :param DataHubHandle hub_handle: Encapsulates to root folder under which this method will instantiate
            a new DataHub object.

        '''



