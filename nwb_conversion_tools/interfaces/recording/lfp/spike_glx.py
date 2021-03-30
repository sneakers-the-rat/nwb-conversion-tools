from spikeextractors import SpikeGLXRecordingExtractor

from nwb_conversion_tools.interfaces.recording.lfp.base_lfp import BaseLFPExtractorInterface


class SpikeGLXLFPInterface(BaseLFPExtractorInterface):
    """Primary data interface class for converting the low-pass (ap) SpikeGLX format."""

    device_name = 'glx'

    RX = SpikeGLXRecordingExtractor