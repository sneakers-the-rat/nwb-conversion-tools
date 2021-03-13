"""Authors: Cody Baker and Ben Dichter."""
from datetime import datetime
from pathlib import Path

from spikeextractors import SpikeGadgetsRecordingExtractor, SubRecordingExtractor

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface


class SpikeGadgetsRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting the high-pass (ap) SpikeGLX format."""

    RX = SpikeGadgetsRecordingExtractor
