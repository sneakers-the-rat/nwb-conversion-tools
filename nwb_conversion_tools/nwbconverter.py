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
        self._spec = {} # type: typing.Dict[tuple, typing.List[typing.Dict, ...]]
        self._metadata_spec = []
        """
        metadata spec objects that parse & return keys and values of metadata rather than represent them directly
        """
        self._static_metadata = {}
        """
        stores static metadata given to :meth:`.add_metadata`
        """

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
                      spec: Optional[BaseSpec] = None,
                      **kwargs):
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
        spec : BaseSpec
            Metadata specifier to parameterize interface object
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
        if len(kwargs) == 0 and spec is None:
            header_str = f'Source Schema for {type(interface).__name__}'
            divider_bar = '-'*len(header_str)
            print('\n'.join((header_str, divider_bar, pformat(source_schema), divider_bar)))
            return

        # check that we have everything with sets
        # combine parameters specified by spec objects and given in kwargs
        specified = list(kwargs.keys())
        if spec is not None:
            specified.extend(spec.specifies)

        if len(set(required) - set(specified)) != 0:
            raise ValueError(f"Not all required parameters are specified,\nRequired:{required}\nSpecified:{specified}")

        self.data_interface_classes[type(interface).__name__] = interface
        spec_key = (interface_type, device_name)
        # prepare dict for storage
        full_spec = {
            'interface': interface,
            'spec': spec,
            'kwargs': dict(kwargs)
        }

        if spec_key not in self._spec.keys():
            self._spec[spec_key] = [full_spec]
        else:
            self._spec[spec_key].append(full_spec)

    def add_metadata(self,
        spec:typing.Union[BaseSpec, str]):
        """

        Parameters
        ----------
        spec : BaseSpec, dict
            if an object that inherits from :class:`.BaseSpec`, then the keys and values of metadata
            are resolved by the object: ie. the keys are the value of :attr:`.BaseSpec.specifies` and
            :meth:`.BaseSpec.parse` returns a dictionary of keys and values.

            if dictionary, assumes static metadata (unchanged across multiple sessions/experiments)
            otherwise, use spec to resolve
            Either a string representing a "top-level" metadata property, or a tuple of nested metadata
            properties like ('NWBFile', 'experimenter')

        Returns
        -------

        """
        if isinstance(spec, dict):
            self._static_metadata = dict_deep_update(self._static_metadata, spec)
        elif issubclass(type(spec), BaseSpec):
            self._metadata_spec.append(spec)
        else:
            raise ValueError(f'Dont know how to handle metadata, needs to be a dictionary of static metadata or a Spec object. got {spec}')





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
            if isinstance(interface, list):
                for subinterface in interface:
                    interface_metadata = subinterface.get_metadata()
                    metadata = dict_deep_update(metadata, interface_metadata)
            else:
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


        # start parsing the specified metadata
        # we'll finish after we instantiate devices, but we need some metadata to specify the devices!
        if metadata is None:
            metadata = self.metadata

        # then from parsing our metadata spec
        for metadata_spec in self._metadata_spec:
            metadata = dict_deep_update(metadata, metadata_spec.parse(base_dir))
        # and finally static kwargs
        metadata = dict_deep_update(metadata, self._static_metadata)

        # instantiate all our devices with their specs!
        for (interface_type, device_name), full_interface_specs in self._spec.items():
            # for each specific type of interface, _spec holds a list of full specification dictionaries
            # with 'interface', 'spec', and 'kwargs' (see add_interface)
            for full_interface_spec in full_interface_specs:
                device_class = full_interface_spec['interface']
                device_kwargs = full_interface_spec['kwargs']
                device_spec = full_interface_spec['spec']
                device_class_name = type(device_class).__name__
                if device_spec is not None:
                    device_kwargs = dict_deep_update(device_kwargs, device_spec.parse(base_dir, metadata))

                interface_instance = device_class(**device_kwargs)

                # add to dict of interfaces. If one already exists, make sure it's a list and append to it
                if device_class_name in self.data_interface_objects.keys():
                    if not isinstance(self.data_interface_objects[device_class_name], list):
                        self.data_interface_objects[device_class_name] = list(self.data_interface_objects[device_class_name])
                    self.data_interface_objects[device_class_name].append(interface_instance)
                else:
                    self.data_interface_objects[device_class_name] = [interface_instance]


        # get metadata from all devices and stuff
        metadata = dict_deep_update(metadata, self.get_metadata())


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
                    if isinstance(data_interface, list):
                        for an_interface in data_interface:
                            an_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))
                    else:
                        data_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))

                io.write(nwbfile)
            print(f"NWB file saved at {nwbfile_path}!")
        else:
            if nwbfile is None:
                nwbfile = make_nwbfile_from_metadata(metadata=metadata)

            for interface_name, data_interface in self.data_interface_objects.items():
                if isinstance(data_interface, list):
                    for an_interface in data_interface:
                        an_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))
                else:
                    data_interface.run_conversion(nwbfile, metadata, **conversion_options.get(interface_name, dict()))

        return nwbfile
