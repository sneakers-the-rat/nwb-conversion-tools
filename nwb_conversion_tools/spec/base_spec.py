from abc import abstractmethod, ABC
import typing

def iter_spec(**kwargs):
    """
    Yield dictionaries of the resolved metadata values for a dict of spec objects
    Parameters
    ----------
    kwargs :

    Returns
    -------

    """
    pass

class BaseSpec(ABC):
    def __init__(self, retype: typing.Optional[typing.Callable] = None):
        """

        Parameters
        ----------
        retype : Callable (optional)

        """
        self.retype = retype

    @abstractmethod
    def parse(self, parsy=None) -> dict:
        """
        All Specs should instantiate a parse method that returns a dictionary of
        metadata variable keys and values. eg::

            >>> BaseSpec().parse()
            { 'subject_id': 'jonny' }

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