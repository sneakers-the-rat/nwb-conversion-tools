"""Authors: Cody Baker and Ben Dichter."""
from abc import ABC

import roiextractors as re
from pynwb import NWBFile
from pynwb.device import Device
from pynwb.ophys import Fluorescence, ImageSegmentation, ImagingPlane, TwoPhotonSeries

from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from nwb_conversion_tools.interfaces.base_data import BaseDataInterface
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature, fill_defaults, get_base_schema


class BaseSegmentationExtractorInterface(BaseDataInterface, ABC):
    SegX = None

    interface_type = 'segmentation'

    @classmethod
    def get_source_schema(cls):
        return get_schema_from_method_signature(cls.SegX.__init__)

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.segmentation_extractor = self.SegX(**source_data)

    def get_metadata_schema(self):
        """Compile metadata schema for the RoiExtractor."""
        metadata_schema = super().get_metadata_schema()
        metadata_schema['required'] = ['Ophys']
        # Initiate Ophys metadata
        metadata_schema['properties']['Ophys'] = get_base_schema()
        metadata_schema['properties']['Ophys']['properties'] = dict(
            Device=get_schema_from_hdmf_class(Device),
            Fluorescence=get_schema_from_hdmf_class(Fluorescence),
            ImageSegmentation=get_schema_from_hdmf_class(ImageSegmentation),
            ImagingPlane=get_schema_from_hdmf_class(ImagingPlane),
            TwoPhotonSeries=get_schema_from_hdmf_class(TwoPhotonSeries)
        )
        metadata_schema['properties']['Ophys']['required'] = \
            ['Device', 'Fluorescence', 'ImageSegmentation']
        fill_defaults(metadata_schema, self.get_metadata())
        return metadata_schema

    def get_metadata(self):
        """Auto-fill metadata with values found from the corresponding roiextractor.
        Must comply with metadata schema."""
        metadata = super().get_metadata()
        metadata.update(re.NwbSegmentationExtractor.get_nwb_metadata(self.segmentation_extractor))
        _ = metadata.pop('NWBFile')
        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata_dict: dict, overwrite: bool = False):
        re.NwbSegmentationExtractor.write_segmentation(
            self.segmentation_extractor,
            nwbfile=nwbfile,
            metadata=metadata_dict,
            overwrite=overwrite
        )
