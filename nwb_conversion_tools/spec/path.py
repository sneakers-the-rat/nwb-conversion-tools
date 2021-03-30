import typing
from copy import copy

from nwb_conversion_tools.spec import BaseSpec
from pathlib import Path as plPath
from threading import Lock
import parse

_BASE_PATH = plPath()
_BASE_PATH_LOCK = Lock()

def base_path(path: typing.Optional[plPath] = None) -> plPath:
    """
    get/set the base path used by Path objects.

    If none has been set, the current directory is used
    (literally ``pathlib.Path()``)

    Parameters
    ----------
    path : :class:`pathlib.Path`
        the base path. if ``None``, get base path

    Returns
    -------
    a copy of :class:`pathlib.Path`
    """
    global _BASE_PATH_LOCK
    global _BASE_PATH

    with _BASE_PATH_LOCK:
        if path is None:
            return copy(_BASE_PATH)
        else:
            _BASE_PATH = plPath(path)





class Path(BaseSpec):
    """
    Specify a metadata variable embedded in a path using :mod:`parse`

    See the `parse documentation <https://github.com/r1chardj0n3s/parse>`_
    for more details, but briefly, to specify the metadata variables
    ``subject_id == 'jonny'`` and ``session_id = '001'``
    in a file path ``data/recordings/jonny_spikes_001.spikes``, one would
    use a ``format == 'data/recordings/{subject_id}_spikes_{session_id}.spikes``.
    Additional options like specifying a format for the values, etc. can be
    found in the parse documentation.

    The path is relative to a base path set by :func:`.base_path`,
    usually by :class:`.NWBConverter` on init. when this object is initializes,
    if the base path is not given on init, it is copied from the global variable
    so it's possible to use more than one base path in an interpreter session...



    """

    def __init__(self, format:str,
                 base:typing.Optional[str]=None,
                 *args, **kwargs):
        super(Path, self).__init__(*args, **kwargs)

        if base is None:
            self.base_path = base_path()
        else:
            self.base_path = plPath(base)

        self.format = format

        self.parser = parse.Parser(self.format)
        if len(self.parser.named_fields) == 0:
            raise ValueError('format string must use named fields, not anonymous fields like {}')

    @property
    def specifies(self) -> typing.Tuple[str,...]:
        return tuple(self.parser.named_fields)

    def parse(self, parsy:typing.Union[str, plPath]) -> dict:
        return self.parser.parse(str(parsy)).named