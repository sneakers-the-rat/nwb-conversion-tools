"""Authors: Cody Baker and Ben Dichter."""
from jsonschema import validate
from pathlib import Path
import typing
from typing import Optional
import warnings
from pprint import pformat

from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject

from .conversion_tools import get_default_nwbfile_metadata, make_nwbfile_from_metadata
from .utils import get_schema_from_hdmf_class, get_schema_for_NWBFile
from .json_schema_utils import dict_deep_update, get_base_schema, fill_defaults, \
    unroot_schema

from nwb_conversion_tools.interfaces import BaseDataInterface, list_interfaces
from nwb_conversion_tools.spec import BaseSpec, parse_nested_spec


class NWBConverter:
    """
    Primary class for all NWB conversion classes.
    """


    def __init__(self, base_dir:Path, source_data: Optional[dict] = None):
        """

        Parameters
        ----------
        base_dir : :class:`pathlib.Path`
            The base directory of the source data, from which all paths are relative
        source_data: dict
            Old style source_data dictionary, kept for compatibility
        """

        self.base_dir = Path(base_dir)

        # preserve compatibility with class-attribute style declaration
        if not hasattr(self, 'data_interface_classes'):
            self.data_interface_classes = {}  # type: dict
        self.data_interface_objects = {} # type: dict

        # init private attributes
        self._metadata = None
        self._dataset_schema = {}
        self._spec = {} # type: typing.Dict[tuple, typing.Tuple[BaseSpec, ...]]
        self._metadata_spec = {}

        # preserve old behavior on init
        if source_data is not None:
            # Validate source_data against source_schema
            validate(instance=source_data, schema=self.get_source_schema())

            # If data is valid, proceed to instantiate DataInterface objects
            self.data_interface_objects = {
                name: data_interface(**source_data[name])
                for name, data_interface in self.data_interface_classes.items()
                if name in source_data
            }

    def add_interface(self, interface_type:Optional[str] = None,
                      device_name: Optional[str] = None,
                      *args):
        """
        Add a recording interface

        Specify interface either with an interface type and name, or else give the class itself as
        ``interface_class``. If both are present, use the class.

        Everything afterwards

        Parameters
        ----------
        interface_type : str
            Type of interface, like 'recording' -- a name of a package in :mod:`~nwb_conversion_tools.interfaces`
        device_name : str
            Name of specific interface, matching the interfaces :attr:`~.interfaces.BaseDataInterface.device_name`
        kwargs :
            kwargs passed to data interface.
        """
        # --------------------------------------------------
        # parse args to get interface
        # --------------------------------------------------

        # otherwise we try to get it programmatically
        if interface_type is not None and device_name is not None:
            interface = list_interfaces(interface_type, device_name)
        else:
            raise ValueError(("Need both interface type and device name",
                              f"got interface_type: {interface_type}, device_name: {device_name}"))

        # get source schema for device to make sure we've specified all the required props
        source_schema = interface.get_source_schema()
        required = source_schema['required']

        # if length of args is zero, assume user is asking for advice on what the heck to do :)
        if len(args) == 0:
            header_str = f'Source Schema for {type(interface).__name__}'
            divider_bar = '-'*len(header_str)
            print('\n'.join((header_str, divider_bar, pformat(source_schema), divider_bar)))
            return

        # otherwise ensure passed specs parameterize all required args
        specs = (arg for arg in args if issubclass(arg, BaseSpec))
        specified = []
        for spec in specs:
            specified.extend(spec.specifies)

        # check that we have everything with sets
        if len(set(required) - set(specified)) != 0:
            raise ValueError(f"Not all required parameters are specified,\nRequired:{required}\nSpecified:{specified}")

        self.data_interface_classes[type(interface).__name__] = interface
        spec_key = (interface_type, device_name)
        if spec_key not in self._spec.keys():
            self._spec[spec_key] = [specs]
        else:
            self._spec[spec_key].append(specs)

    def add_metadata(self,
        key:typing.Union[str, typing.Tuple[str,...]],
        spec:typing.Union[BaseSpec, str]):
        """

        Parameters
        ----------
        key : str, tuple
            Either a string representing a "top-level" metadata property, or a tuple of nested metadata
            properties like ('NWBFile', 'experimenter')
        spec : BaseSpec, str
            if str, assumes static metadata (unchanged across multiple sessions/experiments)
            otherwise, use spec to resolve

        Returns
        -------

        """
        if isinstance(key, str):
            self._metadata_spec[key] = spec
        elif isinstance(key, (tuple, list)) and len(key) == 1:
            self._metadata_spec[key[0]] = spec
        else:
            # add spec to nested dict
            sub_dict = self._metadata_spec
            for i, sub_key in enumerate(key):
                if i < len(key)-1:
                    if sub_key not in sub_dict.keys():
                        sub_dict[sub_key] = {}
                    sub_dict = sub_dict[sub_key]
                else:
                    sub_dict[sub_key] = spec





    # --------------------------------------------------
    # properties
    # --------------------------------------------------
    @property
    def source_schema(self):
        return self.get_source_schema()

    @property
    def metadata_schema(self):
        return self.get_metadata_schema()

    @property
    def conversion_options_schema(self):
        return self.get_conversion_options_schema()

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self.get_metadata()
        return self._metadata

    # --------------------------------------------------
    # schema access methods
    # --------------------------------------------------

    def get_source_schema(self):
        """Compile input schemas from each of the data interface classes."""
        source_schema = get_base_schema(
            root=True,
            id_='source.schema.json',
            title='Source data schema',
            description='Schema for the source data, files and directories',
            version='0.1.0'
        )
        for interface_name, data_interface in self.data_interface_classes.items():
            source_schema['properties'].update(
                {interface_name: unroot_schema(data_interface.get_source_schema())})
        return source_schema

    def get_metadata_schema(self):
        """Compile metadata schemas from each of the data interface objects."""
        metadata_schema = get_base_schema(
            id_='metadata.schema.json',
            root=True,
            title='Metadata',
            description='Schema for the metadata',
            version="0.1.0",
            required=["NWBFile"],
            properties=dict(
                NWBFile=get_schema_for_NWBFile(),
                Subject=get_schema_from_hdmf_class(Subject)
            )
        )
        for data_interface in self.data_interface_objects.values():
            interface_schema = unroot_schema(data_interface.get_metadata_schema())
            metadata_schema = dict_deep_update(metadata_schema, interface_schema)

        fill_defaults(metadata_schema, self.get_metadata())
        return metadata_schema

    def get_conversion_options_schema(self):
        """Compile conversion option schemas from each of the data interface classes."""
        conversion_options_schema = get_base_schema(
            root=True,
            id_='conversion_options.schema.json',
            title="Conversion options schema",
            description="Schema for the conversion options",
            version="0.1.0"
        )
        for interface_name, data_interface in self.data_interface_classes.items():
            conversion_options_schema['properties'].update({
                interface_name: unroot_schema(data_interface.get_conversion_options_schema())
            })
        return conversion_options_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = get_default_nwbfile_metadata()
        for interface in self.data_interface_objects.values():
            interface_metadata = interface.get_metadata()
            metadata = dict_deep_update(metadata, interface_metadata)
        return metadata

    def run_conversion(
            self,
            metadata: Optional[dict] = None,
            nwbfile_path: Optional[str] = None,
            overwrite: Optional[bool] = False,
            nwbfile: Optional[NWBFile] = None,
            conversion_options: Optional[dict] = None,
            base_dir: Optional[Path] = None
    ):
        """
        Run the NWB conversion over all the instantiated data interfaces.

        Parameters
        ----------
        metadata : dict
        nwbfile_path : str, optional
            Location to save the NWBFile, if save_to_file is True. The default is None.
        overwrite : bool, optional
            If True, replaces any existing NWBFile at the nwbfile_path location, if save_to_file is True.
            If False, appends the existing NWBFile at the nwbfile_path location, if save_to_file is True.
            The default is False.
        nwbfile : NWBFile, optional
            A pre-existing NWBFile object to be appended (instead of reading from nwbfile_path).
        conversion_options : dict, optional
            Similar to source_data, a dictionary containing keywords for each interface for which non-default
            conversion specification is requested.

        Returns
        -----------
        nwbfile : NWBFile
            the created NWBFile
        """
        if conversion_options is None:
            conversion_options = dict()
        else:
            validate(instance=conversion_options, schema=self.get_conversion_options_schema())

        if base_dir is not None:
            base_dir = Path(base_dir)
        else:
            base_dir = self.base_dir

        # instantiate all our devices with their specs!
        for (interface_type, device_name), interface_spec in self._spec.items():
            device_class = list_interfaces(interface_type, device_name)
            device_kwargs = {}
            for a_spec in interface_spec:
                device_kwargs.update(a_spec.parse(base_dir))

            self.data_interface_objects[type(device_class).__name__] = device_class(**device_kwargs)

        # parse metadata
        if metadata is None:
            metadata = self.metadata

        # get metadata from all devices and stuff
        metadata = dict_deep_update(metadata, self.get_metadata())
        # then from parsing our metadata spec
        metadata = dict_deep_update(metadata, parse_nested_spec(self._metadata_spec, base_dir))

        if nwbfile_path is not None:

            if Path(nwbfile_path).is_file() and not overwrite:
                mode = "r+"
            else:
                mode = "w"

            with NWBHDF5IO(nwbfile_path, mode=mode) as io:
                if mode == "r+":
                    nwbfile = io.read()
                elif nwbfile is None:
                    nwbfile = make_nwbfile_from_metadata(metadata=metadata)

                for interface_name, data_interface in self.data_interface_objects.items():
                    data_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))

                io.write(nwbfile)
            print(f"NWB file saved at {nwbfile_path}!")
        else:
            if nwbfile is None:
                nwbfile = make_nwbfile_from_metadata(metadata=metadata)
            for interface_name, data_interface in self.data_interface_objects.items():
                data_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))

        return nwbfile
