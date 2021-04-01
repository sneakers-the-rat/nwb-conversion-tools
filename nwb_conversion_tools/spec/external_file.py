"""
Specify metadata that's in a separate, external file from the standard format files
"""
import typing
from pathlib import Path
from abc import abstractmethod
import json

from nwb_conversion_tools.spec import BaseSpec

class BaseExternalFileSpec(BaseSpec):

    loaded_files = {}


    def __init__(self, path:Path,
                 key: str,
                 field:typing.Union[str, typing.Tuple[str, ...]],
                 cache:bool = True,
                 *args, **kwargs):
        """

        Parameters
        ----------
        self :
        path : path relative to base_dir that is passed in :meth:`._parse`
        key :
        field :
        cache : bool
            if True, store loaded file in :attr:`.loaded_files` dictionary to prevent
            re-load if another spec needs it.
        kwargs :

        Returns
        -------

        """
        super(BaseExternalFileSpec, self).__init__(*args, **kwargs)

        self.path = Path(path)
        self.key = key
        self.field = field
        self.cache = cache

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

    @property
    def _specifies(self):
        return tuple(self.key)

    def _sub_select(self, loaded_file:dict) -> typing.Any:
        """
        Use :attr:`.field` to select from the loaded_file

        Parameters
        ----------
        loaded_file :

        Returns
        -------

        """
        # slice the loaded file to get the value of interest
        sub_select = {}
        if isinstance(self.field, (tuple, list)):
            # to avoid copying what could potentially be a large dict,
            # but also avoid modifying the cached one, do this sorta awkward shit
            for i, item in enumerate(self.field):
                if i == 0:
                    sub_select = loaded_file[item]
                else:
                    sub_select = sub_select[item]
        else:
            # if we just got a string or an int or something give it a shot
            sub_select = loaded_file[self.field]
        return sub_select

    def _parse(self, base_path:Path, metadata:typing.Optional[dict]=None) -> dict:
        # get abs path
        base_path = Path(base_path).absolute()
        file_path = (base_path / self.path).absolute()

        # if cache is on, try to retrieve from cache
        if self.cache and file_path in self.loaded_files.keys():
            loaded_file = self.loaded_files[file_path]
        else:
            # otherwise load file
            loaded_file = self._load_file(file_path)
            if self.cache:
                self.loaded_files[file_path] = loaded_file

        return {self.key:self._sub_select(loaded_file)}

class JSON(BaseExternalFileSpec):

    def __init__(self, hook:typing.Optional[typing.Callable]=None,
                 *args, **kwargs):
        """
        Load a field from a .json file. see base class for docs

        Parameters
        ----------
        hook : Optionally, include some callable function to use as the fallback
            object loader hook (see ``object_hook`` argument in ``json.load`` for more information)
        args : passed to :class:`.BaseExternalFileSpec`
        kwargs :
        """
        self.hook = hook
        super(JSON, self).__init__(*args, **kwargs)

    def _load_file(self, path:Path) -> dict:
        with open(path, 'r') as p:
            loaded = json.load(p, object_hook=self.hook)
        return loaded

class Mat(BaseExternalFileSpec):
    pass

class YAML(BaseExternalFileSpec):
    pass