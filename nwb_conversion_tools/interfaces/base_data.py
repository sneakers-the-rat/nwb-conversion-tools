"""Authors: Cody Baker and Ben Dichter."""
from abc import abstractmethod, ABC
import warnings

from nwb_conversion_tools.json_schema_utils import (
    get_base_schema, get_schema_from_method_signature, fill_defaults)


class BaseDataInterface(ABC):

    interface_type = '' # type: str
    """
    A category of interface, like recording, segmentation, sorting, etc. 
    
    Typically corresponds to the inheritance/module structure of the interface class
    (eg. 'recording' objects inherit from :class:`.BaseRecordingExtractorInterface`)
    """

    device_name = '' # type: str
    """
    A human-readable device name used by :func:`.interfaces.list_interfaces` to
    identify it. Should be overridden by any interface class that's a "leaf"
    intended to be instantiated by itself (metaclasses should leave blank).
    
    Names can be redundant, but should be unique within an interface type. ie.
    there should only one device with device_name per 'recording' or 'segmentation'
    types.
    """

    @classmethod
    def get_source_schema(cls):
        return get_base_schema()

    @classmethod
    def get_conversion_options_schema(cls):
        return get_schema_from_method_signature(cls.run_conversion, exclude=['nwbfile', 'metadata'])

    def __init__(self, **source_data):
        self.source_data = source_data

    def get_metadata_schema(self):
        metadata_schema = get_base_schema(
            id_='metadata.schema.json',
            root=True,
            title='Metadata',
            description='Schema for the metadata',
            version="0.1.0",
        )
        return metadata_schema

    def get_metadata(self):
        return dict()

    @abstractmethod
    def run_conversion(self, nwbfile_path: str, metadata: dict, **conversion_options):
        pass

    def convert_data(self, nwbfile_path, metadata, **conversion_options):
        warnings.warn("The convert_data method should now be renamed to run_conversion "
                      "as of nwb-conversion-tools v0.6.0", DeprecationWarning)
        self.run_conversion(nwbfile_path, metadata, **conversion_options)
