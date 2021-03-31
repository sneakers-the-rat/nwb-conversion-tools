import typing
from copy import copy
import re
import sys

from nwb_conversion_tools.spec import BaseSpec
from nwb_conversion_tools.utils import _dedupe_list_of_dicts, AmbiguityError
from pathlib import Path as plPath
from threading import Lock
import parse
import glob
#
# _BASE_PATH = plPath()
# _BASE_PATH_LOCK = Lock()
#
# def base_path(path: typing.Optional[plPath] = None) -> plPath:
#     """
#     get/set the base path used by Path objects.
#
#     If none has been set, the current directory is used
#     (literally ``pathlib.Path()``)
#
#     Parameters
#     ----------
#     path : :class:`pathlib.Path`
#         the base path. if ``None``, get base path
#
#     Returns
#     -------
#     a copy of :class:`pathlib.Path`
#     """
#     global _BASE_PATH_LOCK
#     global _BASE_PATH
#
#     with _BASE_PATH_LOCK:
#         if path is None:
#             return copy(_BASE_PATH)
#         else:
#             _BASE_PATH = plPath(path).absolute()
#




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

    Raises an exception if multiple matching values are found in :meth:`.Path.parse` ,
    this is the singular version, and if there are multiple matches that means it's mis-specified
    To allow multiple matches, try :class:`.Paths`

    .. todo::

        This should be renamed something like MetaInPath or something, and then
        Path and Paths should be things that are basically globs with constraints.
        jonny is just very tired rn
    """

    def __init__(self, format:str,
                 *args, **kwargs):
        super(Path, self).__init__(*args, **kwargs)

        self.format = str(format)
        self.parser = parse.Parser(self.format) # type: typing.Optional[parse.Parser]

        if len(self.parser.named_fields) == 0:
            raise ValueError('format string must use named fields, not anonymous fields like {}')

    @property
    def specifies(self) -> typing.Tuple[str,...]:
        return tuple(self.parser.named_fields)

    def _parse_dir(self, base_path:typing.Union[str, plPath]) -> list:
        """
        First part of :meth:`.Path.parse` , given a base directory and parser,
        return a list of dicts of matching keys found.
        """
        # make absolute
        base_path = plPath(base_path).absolute()
        # globify format string to find all matching files
        format_glob = re.sub(r'\{.*?\}', '*', self.format)

        # find matching files relative to the base_path
        matching_files = base_path.glob(format_glob)

        # parse results
        results = []
        for match in matching_files:
            # make relative to base_path to match format
            match = match.relative_to(base_path)
            parsed = self.parser.parse(str(match))
            # parser returns None if no matches
            if parsed is not None:
                results.append(parsed.named)

        if len(results) == 0:
            raise ValueError(f'No matches were found between \n(relative) format:\n{self.format}\nin\n{base_path}')

        return results


    def parse(self, base_path:typing.Union[str, plPath]) -> dict:
        """
        Parse metadata stored in some path name relative to
         using the parser created by :attr:`.format`.

        If the input path is not absolute, it is made absolute relative to
        :attr:`.base_path` so that it matches :attr:`.format`

        Raises a :class:`~.utils.AmbiguityError` if multiple matches for a single
        key are found, and a ``ValueError`` if zero matches are found.

        Parameters
        ----------
        base_path : :class:`pathlib.Path`
            Path to parse!!!

        Returns
        -------
        dict of metadata params
        """
        results = self._parse_dir(base_path)

        # check for dupes!!
        try:
            results = _dedupe_list_of_dicts(results, raise_on_dupes=True)
        except AmbiguityError as e:
            # reraise error with additional informative message about what else to use
            raise type(e)(
                str(e)+'\nIf this was intentional, you might want to try spec.Paths'
            ).with_traceback(sys.exc_info()[2])

        return results

class Paths(Path):
    """
    Like :class:`.spec.Path` but allows multiple values for a single key
    """

    def parse(self, base_path: typing.Union[str, plPath]) -> dict:
        results = self._parse_dir(base_path)
        return _dedupe_list_of_dicts(results, raise_on_dupes=False)
