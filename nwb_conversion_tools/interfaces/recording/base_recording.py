"""Authors: Cody Baker and Ben Dichter."""
from abc import ABC
from typing import Union
from pathlib import Path

import spikeextractors as se
from pynwb import NWBFile
from pynwb.device import Device
from pynwb.ecephys import ElectrodeGroup, ElectricalSeries

from nwb_conversion_tools.interfaces.base_data import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from nwb_conversion_tools.json_schema_utils import get_schema_from_method_signature, fill_defaults, get_base_schema

PathType = Union[str, Path, None]


class BaseRecordingExtractorInterface(BaseDataInterface, ABC):
    """Primary class for all RecordingExtractorInterfaces."""

    interface_type = 'recording'

    RX = None

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        return get_schema_from_method_signature(cls.RX.__init__)

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.recording_extractor = self.RX(**source_data)
        self.subset_channels = None
        self.source_data = source_data

    def get_metadata_schema(self):
        """Compile metadata schema for the RecordingExtractor."""
        metadata_schema = super().get_metadata_schema()

        # Initiate Ecephys metadata
        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')
        metadata_schema['properties']['Ecephys']['properties'] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ElectrodeGroup=get_schema_from_hdmf_class(ElectrodeGroup),
            ElectricalSeries=get_schema_from_hdmf_class(ElectricalSeries)
        )
        metadata_schema['properties']['Ecephys']['required'] = ['Device', 'ElectrodeGroup', 'ElectricalSeries']
        fill_defaults(metadata_schema, self.get_metadata())
        return metadata_schema

    def subset_recording(self, stub_test: bool = False):
        """
        Subset a recording extractor according to stub and channel subset options.

        Parameters
        ----------
        stub_test : bool, optional (default False)
        """
        kwargs = dict()

        if stub_test:
            num_frames = 100
            end_frame = min([num_frames, self.recording_extractor.get_num_frames()])
            kwargs.update(end_frame=end_frame)

        if self.subset_channels is not None:
            kwargs.update(channel_ids=self.subset_channels)

        recording_extractor = se.SubRecordingExtractor(
            self.recording_extractor,
            **kwargs
        )
        return recording_extractor

    def run_conversion(
      self,
      nwbfile: NWBFile,
      metadata: dict = None,
      stub_test: bool = False,
      use_times: bool = False, 
      write_as_lfp: bool = False,
      save_path: PathType = None, 
      overwrite: bool = False,
      buffer_mb: int = 500
    ):
        """
        Primary function for converting recording extractor data to nwb.

        Parameters
        ----------
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format::

                metadata['Ecephys']['ElectricalSeries'] = {
                    'name': my_name,
                     'description': my_description
                }

        use_times: bool
            If True, the times are saved to the nwb file using recording.frame_to_time(). If False (default),
            the sampling rate is used.
        write_as_lfp: bool (optional, defaults to False)
            If True, writes the traces under a processing LFP module in the NWBFile instead of acquisition.
        save_path: PathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        buffer_mb: int (optional, defaults to 500MB)
            Maximum amount of memory (in MB) to use per iteration of the internal DataChunkIterator.
            Requires trace data in the RecordingExtractor to be a memmap object.
        """
        if stub_test or self.subset_channels is not None:
            recording = self.subset_recording(stub_test=stub_test)
        else:
            recording = self.recording_extractor

        se.NwbRecordingExtractor.write_recording(
            recording=recording,
            nwbfile=nwbfile,
            metadata=metadata,
            use_times=use_times,
            write_as_lfp=write_as_lfp,
            save_path=save_path,
            overwrite=overwrite,
            buffer_mb=buffer_mb
        )
