"""Authors: Cody Baker, Ben Dichter and Luiz Tauffer."""
from datetime import datetime
import pkgutil
import importlib
from pathlib import Path
import typing
import inspect
from abc import ABC

import numpy as np
import pynwb

from .json_schema_utils import get_base_schema


def get_schema_from_hdmf_class(hdmf_class):
    """Get metadata schema from hdmf class."""
    schema = get_base_schema()
    schema['tag'] = hdmf_class.__module__ + '.' + hdmf_class.__name__

    # Detect child-like (as opposed to link) fields
    pynwb_children_fields = [f['name'] for f in hdmf_class.get_fields_conf() if f.get('child', False)]
    # For MultiContainerInterface
    if hasattr(hdmf_class, '__clsconf__'):
        pynwb_children_fields.append(hdmf_class.__clsconf__['attr'])

    # Temporary solution before this is solved: https://github.com/hdmf-dev/hdmf/issues/475
    if 'device' in pynwb_children_fields:
        pynwb_children_fields.remove('device')

    docval = hdmf_class.__init__.__docval__
    for docval_arg in docval['args']:
        schema_arg = {docval_arg['name']: dict(description=docval_arg['doc'])}

        # type float
        if docval_arg['type'] == 'float' \
            or (isinstance(docval_arg['type'], tuple)
                and any([it in docval_arg['type'] for it in [float, 'float']])):
            schema_arg[docval_arg['name']].update(type='number')

        # type string
        elif docval_arg['type'] is str \
            or (isinstance(docval_arg['type'], tuple)
                and str in docval_arg['type']):
            schema_arg[docval_arg['name']].update(type='string')

        # type datetime
        elif docval_arg['type'] is datetime \
            or (isinstance(docval_arg['type'], tuple)
                and datetime in docval_arg['type']):
            schema_arg[docval_arg['name']].update(type='string', format='date-time')

        # if TimeSeries, skip it
        elif docval_arg['type'] is pynwb.base.TimeSeries \
            or (isinstance(docval_arg['type'], tuple)
                and pynwb.base.TimeSeries in docval_arg['type']):
            continue

        # if PlaneSegmentation, skip it
        elif docval_arg['type'] is pynwb.ophys.PlaneSegmentation or \
                (isinstance(docval_arg['type'], tuple) and
                 pynwb.ophys.PlaneSegmentation in docval_arg['type']):
            continue

        else:
            if not isinstance(docval_arg['type'], tuple):
                docval_arg_type = [docval_arg['type']]
            else:
                docval_arg_type = docval_arg['type']

            # if another nwb object (or list of nwb objects)
            if any([hasattr(t, '__nwbfields__') for t in docval_arg_type]):
                is_nwb = [hasattr(t, '__nwbfields__') for t in docval_arg_type]
                item = docval_arg_type[np.where(is_nwb)[0][0]]
                # if it is child
                if docval_arg['name'] in pynwb_children_fields:
                    items = [get_schema_from_hdmf_class(item)]
                    schema_arg[docval_arg['name']].update(
                        type='array', items=items, minItems=1, maxItems=1
                    )
                # if it is link
                else:
                    target = item.__module__ + '.' + item.__name__
                    schema_arg[docval_arg['name']].update(
                        type='string',
                        target=target
                    )
            else:
                continue

        # Check for default arguments
        if 'default' in docval_arg:
            if docval_arg['default'] is not None:
                schema_arg[docval_arg['name']].update(default=docval_arg['default'])
        else:
            schema['required'].append(docval_arg['name'])

        schema['properties'].update(schema_arg)

    if 'allow_extra' in docval:
        schema['additionalProperties'] = docval['allow_extra']

    return schema


def get_schema_for_NWBFile():
    schema = get_base_schema()
    schema['tag'] = 'pynwb.file.NWBFile'
    schema['required'] = ["session_description", "identifier", "session_start_time"]
    schema['properties'] = {
        "session_description": {
            "type": "string",
            "format": "long",
            "description": "a description of the session where this data was generated"
        },
        "identifier": {
            "type": "string",
            "description": "a unique text identifier for the file"
        },
        "session_start_time": {
            "type": "string",
            "description": "the start date and time of the recording session",
            "format": "date-time"
        },
        "experimenter": {
            "type": "array",
            "items": {"type": "string", "title": "experimenter"},
            "description": "name of person who performed experiment"
        },
        "experiment_description": {
            "type": "string",
            "description": "general description of the experiment"
        },
        "session_id": {
            "type": "string",
            "description": "lab-specific ID for the session"
        },
        "institution": {
            "type": "string",
            "description": "institution(s) where experiment is performed"
        },
        "notes": {
            "type": "string",
            "description": "Notes about the experiment."
        },
        "pharmacology": {
            "type": "string",
            "description": "Description of drugs used, including how and when they were administered. Anesthesia(s), "
                           "painkiller(s), etc., plus dosage, concentration, etc."
        },
        "protocol": {
            "type": "string",
            "description": "Experimental protocol, if applicable. E.g., include IACUC protocol"
        },
        "related_publications": {
            "type": "string",
            "description": "Publication information.PMID, DOI, URL, etc. If multiple, concatenate together and describe"
                           " which is which. such as PMID, DOI, URL, etc"
        },
        "slices": {
            "type": "string",
            "description": "Description of slices, including information about preparation thickness, orientation, "
                           "temperature and bath solution"
        },
        "source_script": {
            "type": "string",
            "description": "Script file used to create this NWB file."
        },
        "source_script_file_name": {
            "type": "string",
            "description": "Name of the source_script file"
        },
        "data_collection": {
            "type": "string",
            "description": "Notes about data collection and analysis."
        },
        "surgery": {
            "type": "string",
            "description": "Narrative description about surgery/surgeries, including date(s) and who performed surgery."
        },
        "virus": {
            "type": "string",
            "description": "Information about virus(es) used in experiments, including virus ID, source, date made, "
                           "injection location, volume, etc."
        },
        "stimulus_notes": {
            "type": "string",
            "description": "Notes about stimuli, such as how and where presented."
        },
        "lab": {
            "type": "string",
            "description": "lab where experiment was performed"
        }
    }
    return schema



def _recurse_subclasses(cls, leaves_only=True) -> list:
    """
    Given some class, find its subclasses recursively

    See: https://stackoverflow.com/a/17246726/13113166

    Args:
        leave_only (bool): If True, only include classes that have no further subclasses,
        if False, return all subclasses.

    Returns:
        list of subclasses
    """

    all_subclasses = []

    for subclass in cls.__subclasses__():
        if leaves_only:
            if len(subclass.__subclasses__()) == 0:
                all_subclasses.append(subclass)
        else:
            all_subclasses.append(subclass)
        all_subclasses.extend(_recurse_subclasses(subclass))

    return all_subclasses

def _recursive_import(module_name:str) -> typing.List[str]:
    """
    Given some path in a python package, import all modules beneath it

    Args:
        module_name (str): name of module to recursively import

    Returns:
        list of all modules that were imported
    """

    # iterate through modules, importing
    # see https://codereview.stackexchange.com/a/70282


    # import module (shouldnt hurt if it has already)
    base_mod = importlib.import_module(module_name)

    pkg_dir = Path(inspect.getsourcefile(base_mod)).resolve().parent

    loaded_modules = []
    for (module_loader, name, ispkg) in pkgutil.walk_packages([pkg_dir], base_mod.__package__+'.'):
        if not ispkg:
            importlib.import_module(name)
            loaded_modules.append(name)

    return loaded_modules

def _gather_list_of_dicts(a_list:list) -> typing.Dict[str, list]:
    """
    Gather a list of dictionaries like::

        [{'key1':'val1'}, {'key1':'val2'}, {'key1':'val3'}]

    to a dict of lists like:

        {'key1': ['val1', 'val2', 'val3']}
    """
    if len(a_list) == 1:
        # if there's only one dict in here just return it lmao
        return a_list[0]

    out_dict = {}
    for inner_dict in a_list:
        for inner_key, inner_value in inner_dict.items():
            if inner_key not in out_dict.keys():
                out_dict[inner_key] = [inner_value]
            else:
                out_dict[inner_key].append(inner_value)

    return out_dict

def _recursive_dedupe_dicts(a_dict, raise_on_dupes=True):
    """
    Deduplicate a list of dicts.

    Optionally raise an exception if duplicates are found, otherwise
    call ``set`` and unwrap singletons and return

    .. todo::

        TEST ME!!!!

    Parameters
    ----------
    a_dict : of dicts

    Returns
    -------
    dict: deduplicated dictionary

    """

    gathered = {k:tuple(set(v)) for k, v in a_dict.items()}
    gathered = {}

    dupes = {}
    for k, v in a_dict.items():
        if isinstance(v, dict):
            gathered[k] = _recursive_dedupe_dicts(v)
        elif isinstance(v, (tuple, list)):
            v = tuple(set(v))
            if len(v)>1:
                dupes[k] = v
                gathered[k] = v
            else:
                gathered[k] = v[0]
        else:
            gathered[k] = v

    if raise_on_dupes and len(dupes)>0:
        dup_str = '\n'.join([f"{k}: {v}" for k, v in dupes.items()])
        raise Exception('Duplicates detected for keys, with values:'+dup_str)

    return gathered

class AmbiguityError(Exception):
    pass

class IntrospectionMixin(object):
    """
    Mixin to allow objects to become aware of all the arguments they were called with on initialization

    Call :meth:`._get_init_args` in the __init__ method of any object that inherits from this mixin :)
    """

    @property
    def _full_sig_names(self):
        """
        Introspect child objects and parents to get all argument names in signature

        Returns
        -------
        list of all argument names
        """
        parents = inspect.getmro(type(self))
        # get signatures for each
        # go in reverse order so top classes options come first
        # list to keep track of parameter names to remove duplicates
        param_names = []
        for cls in reversed(parents):
            sig = inspect.signature(cls)
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'kwargs', 'args'):
                    continue
                if param_name not in param_names:
                    # check if we already have a parameter with this name,
                    # if we don't add it.
                    param_names.append(param_name)

        return param_names

    def _get_init_args(self):
        """
        introspect object and get all arguments passed on __init__

        depends on introspecting up frames so should only be called *during* the top-level __init__
        of the base class :)

        Returns
        -------
        dict of argument names and params
        """

        param_names = self._full_sig_names

        # iterate from back to front (top frame to low frame) getting args
        #
        params = {}
        for frame_info in reversed(inspect.stack()):
            frame = frame_info.frame
            frame_locals = inspect.getargvalues(frame).locals
            frame_params = {k:v for k, v in frame_locals.items() if k in param_names}
            params.update(frame_params)

        return params

    def _full_name(self):
        """
        Returns the full module and class name of an object, eg.
        ``nwb_conversion_tools.spec.external_file.JSON``

        Returns
        -------
        str
        """
        return '.'.join((self.__module__, type(self).__name__))





