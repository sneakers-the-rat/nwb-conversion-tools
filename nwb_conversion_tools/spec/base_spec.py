from abc import abstractmethod, ABC
import typing
import gc


class BaseSpec(ABC):
    def __init__(self, retype: typing.Optional[typing.Callable] = None, *args, **kwargs):
        """

        Parameters
        ----------
        retype : Callable (optional)

        """
        self.retype = retype

    @abstractmethod
    def parse(self, base_path=None) -> dict:
        """
        All Specs should instantiate a parse method that returns a dictionary of
        metadata variable keys and values. eg::

            >>> BaseSpec().parse()
            { 'subject_id': 'jonny' }

        The typical use is to be able to specify some metadata values
        that are contained ***somewhere*** relative to a directory of data, so
        the passed argument should typically be that directory.
        """

    @property
    @abstractmethod
    def specifies(self) -> typing.Tuple[str, ...]:
        """
        Which metadata variables are specified by this Spec object

        Returns
        -------
        tuple of strings
        """


