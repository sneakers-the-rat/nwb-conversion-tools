from abc import abstractmethod, ABC
import typing
import gc
import types
from pathlib import Path
from nwb_conversion_tools.json_schema_utils import dict_deep_update


class BaseSpec(ABC):
    def __init__(self, retype: typing.Optional[typing.Callable] = None, *args, **kwargs):
        """

        Parameters
        ----------
        retype : Callable (optional)

        """
        self._child = None
        self._parse_ref = None
        self._parent = None # type: typing.Optional[BaseSpec]


        self.retype = retype

    def parse(self, base_path:Path) -> dict:
        """
        Parse all parameters from self and child :meth:`._parse` methods,
        combining into single dictionary

        Returns
        -------

        """
        out = self._parse(base_path)

        if self._child is not None:
            for child in self.children():
                out = dict_deep_update(out, child._parse())

        return out


    @abstractmethod
    def _parse(self, base_path=None)      -> dict:
        """
        All Specs should instantiate a _parse method that returns a dictionary of
        metadata variable keys and values. eg::

            >>> BaseSpec().parse()
            { 'subject_id': 'jonny' }

        The typical use is to be able to specify some metadata values
        that are contained ***somewhere*** relative to a directory of data, so
        the passed argument should typically be that directory.
        """

    @property
    def specifies(self) -> typing.Tuple[str,...]:
        """
        Which metadata variables are specified by this Spec object and its children

        Returns
        -------
        tuple of strings
        """
        specified = list(self._specifies)

        if self._child is not None:
            for child in self.children():
                specified.extend(list(child._specifies))

        return tuple(specified)


    @property
    @abstractmethod
    def _specifies(self) -> typing.Tuple[str, ...]:
        """
        Which metadata variables are specified by this Spec object

        Returns
        -------
        tuple of strings
        """

    @property
    def parent(self) -> 'BaseSpec':
        return self._parent

    @parent.setter
    def parent(self, parent:'BaseSpec'):
        if not issubclass(type(parent), BaseSpec):
            raise TypeError('parents must be subclasses of BaseSpec')
        self._parent = parent

    def children(self) -> typing.Iterable['BaseSpec']:
        """
        Generator for iterating over children (added)

        Returns
        -------

        """
        if self._child is None:
            return

        active_child = self._child
        yield active_child

        while active_child._child is not None:
            active_child = active_child._child
            yield active_child


    def __add__(self, other:'BaseSpec'):
        if not issubclass(type(other), BaseSpec):
            raise TypeError('can only add subclasses of BaseSpec')

        if self._child is None:
            # if we haven't been chained at all yet, claim the child
            self._child = other
            self._child.parent = self

        else:
            # we already have a child,
            # add it to our child instead (potentially recursively)
            self._child = self._child + other

        return self





