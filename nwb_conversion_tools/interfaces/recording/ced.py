"""Authors: Luiz Tauffer"""
import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.base_recording import BaseRecordingExtractorInterface
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature


class CEDRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a CEDRecordingExtractor."""

    device_name = 'ced'

    RX = se.CEDRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        source_schema = get_schema_from_method_signature(
            class_method=cls.RX.__init__,
            exclude=['smrx_channel_ids']
        )
        source_schema.update(additionalProperties=True)
        source_schema['properties'].update(
            file_path=dict(
                type=source_schema['properties']['file_path']['type'],
                format="file",
                description="path to data file"
            )
        )

        return source_schema

    @classmethod
    def get_all_channels_info(cls, file_path):
        return cls.RX.get_all_channels_info(file_path)
