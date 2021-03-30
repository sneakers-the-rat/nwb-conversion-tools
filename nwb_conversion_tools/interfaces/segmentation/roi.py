from roiextractors import CnmfeSegmentationExtractor, ExtractSegmentationExtractor, \
    CaimanSegmentationExtractor, Suite2pSegmentationExtractor, SimaSegmentationExtractor

from nwb_conversion_tools.interfaces.segmentation.base_segmentation import BaseSegmentationExtractorInterface


class CnmfeSegmentationInterface(BaseSegmentationExtractorInterface):
    """Data interface for CnmfeRecordingInterface"""

    device_name = 'cnmfe'

    SegX = CnmfeSegmentationExtractor


class ExtractSegmentationInterface(BaseSegmentationExtractorInterface):
    """Data interface for ExtractSegmentationExtractor"""

    device_name = 'extract'

    SegX = ExtractSegmentationExtractor


class CaimanSegmentationInterface(BaseSegmentationExtractorInterface):
    """Data interface for CaimanSegmentationExtractor"""

    device_name = 'caiman'

    SegX = CaimanSegmentationExtractor


class Suite2pSegmentationInterface(BaseSegmentationExtractorInterface):
    """Data interface for Suite2pSegmentationExtractor"""

    device_name = 'suite2p'

    SegX = Suite2pSegmentationExtractor


class SimaSegmentationInterface(BaseSegmentationExtractorInterface):
    """Data interface for SimaSegmentationExtractor"""

    device_name = 'sima'

    SegX = SimaSegmentationExtractor
