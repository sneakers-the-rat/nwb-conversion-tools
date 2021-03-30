"""
Specify metadata that's in a separate, external file from the standard format files
"""
import typing
from pathlib import Path
from abc import abstractmethod

from nwb_conversion_tools.spec import BaseSpec

def BaseExternalFileSpec(BaseSpec):

    def __init__(self, path:Path,
                 key: str,
                 field:typing.Union[str, typing.Tuple[str, ...]],
                 *args, **kwargs):
        super(BaseExternalFileSpec, self).__init__(*args, **kwargs)

        self.path = Path(path)
        self.field = field

    @abstractmethod
    def _load_file(self, path:Path) -> dict:
        """
        Load the file and return it as a nested dictionary of dictionaries or tuples

        such that it can be indexed by successively slicing with :attr:`.field`

        Parameters
        ----------
        self :
        key : str
            name of the property that will be returned
        path :

        Returns
        -------

        """

        pass


def JSON(BaseExternalFileSpec):
    pass

def Mat(BaseExternalFileSpec):
    pass

def YAML(BaseExternalFileSpec):
    pass