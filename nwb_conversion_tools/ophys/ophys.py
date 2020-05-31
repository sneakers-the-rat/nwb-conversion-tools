import numpy as np
import yaml
from pynwb.ophys import OpticalChannel, ImageSegmentation, ImagingPlane, TwoPhotonSeries, Fluorescence, DfOverF
from pynwb.device import Device
from segmentationextractors.nwbextractor.nwbsegmentationextractor import iter_datasetvieww
from nwb_conversion_tools.converter import NWBConverter
from hdmf.data_utils import DataChunkIterator

class OphysNWBConverter(NWBConverter):

    def __init__(self, metadata, nwbfile=None, source_paths=None):

        super(OphysNWBConverter, self).__init__(metadata, nwbfile=nwbfile, source_paths=source_paths)

        # device = Device('microscope')
        # self.nwbfile.add_device(device)
        # self.imaging_plane = self.add_imaging_plane()
        # self.two_photon_series = self.create_two_photon_series()
        self.ophys_mod = self.nwbfile.create_processing_module('Ophys', 'contains optical physiology processed data')

    def create_optical_channel(self, metadata=None):

        if metadata==[]:
            metadata = None
        input_kwargs = dict(
            name='OpticalChannel',
            description='no description',
            emission_lambda=np.nan
        )

        if metadata:
            input_kwargs.update(metadata)

        return OpticalChannel(**input_kwargs)

    def add_imaging_plane(self, metadata=None, optical_channel=None):

        input_kwargs = dict(
            name='ImagingPlane',
            description='no description',
            device=self.devices[list(self.devices.keys())[0]],
            excitation_lambda=np.nan,
            imaging_rate=1.0,
            indicator='unknown',
            location='unknown'
        )
        if metadata is None and 'Ophys' in self.metadata and 'ImagingPlane' in self.metadata['Ophys']:
            metadata = self.metadata['Ophys']['ImagingPlane'][0]
            if metadata.get('device'):
                metadata['device'] = self.nwbfile.devices[metadata['device']]
            if metadata.get('optical_channel'):
                if len(metadata['optical_channel'])>0:
                    metadata['optical_channel'] = [self.create_optical_channel(metadata=i) for i in metadata['optical_channel']]
            else:
                metadata['optical_channel'] = self.create_optical_channel()
        if metadata:
            input_kwargs.update(metadata)
        self.nwbfile.add_imaging_plane(ImagingPlane(**input_kwargs))

        return self.nwbfile.get_imaging_plane(name=input_kwargs['name'])


class ProcessedOphysNWBConverter(OphysNWBConverter):

    def __init__(self, metadata, nwbfile=None, source_paths=None):
        super(ProcessedOphysNWBConverter, self).__init__(metadata, nwbfile=nwbfile, source_paths=source_paths)

        self.image_segmentation = self.create_image_segmentation()
        self.ophys_mod.add_data_interface(self.image_segmentation)

    def create_image_segmentation(self):
        if 'ImageSegmentation' in self.metadata.get('Ophys','not_found'):
            return ImageSegmentation(name=self.metadata['Ophys']['ImageSegmentation']['name'])
        else:
            return ImageSegmentation()

    def create_plane_segmentation(self, metadata=None):
        # TODO: implement multiple PlaneSegmentations
        input_kwargs = dict(
            name='PlaneSegmentation',
            description='output from segmenting my favorite imaging plane',
            imaging_plane=self.imaging_plane
        )

        if metadata:
            input_kwargs.update(metadata)
        elif 'Ophys' in self.metadata and 'plane_segmentations' in self.metadata['Ophys']['ImageSegmentation']:
            metadata = self.metadata['Ophys']['ImageSegmentation']['plane_segmentations'][0]
            if metadata.get('imaging_planes'):
                metadata['imaging_plane'] = self.nwbfile.get_imaging_plane(name=metadata['imaging_planes'])
                metadata.pop('imaging_planes')  # TODO this will change when loopis implemented
            else:
                metadata['imaging_plane'] = self.nwbfile.get_imaging_plane(
                    name=list(self.nwbfile.imaging_planes.keys())[0])
        if metadata:
            input_kwargs.update(metadata)

        self.plane_segmentation = self.image_segmentation.create_plane_segmentation(**input_kwargs)
        

class SegmentationExtractor2NWBConverter(ProcessedOphysNWBConverter):
    
    def __init__(self, source_path, nwbfile, metadata):
        """
        Conversion of Sima segmentationExtractor object to an NWB file using GUI
        Parameters
        ----------
        source_path: list
            list of paths to data sources eg. ['file1.ext','file2.ext']
        nwbfile: NWBfile
            pre-existing nwb file to append all the data to
        metadata: str
            location of the metadata.yaml file that can be used to populate nwb file metadata.
        """
        if isinstance(metadata,str):
            with open(metadata,'r') as f:
                metadata = yaml.safe_load(f)
        super().__init__(metadata,nwbfile,source_path)
        self.auto_create_dict = dict(imaging_plane=False,
                                     two_photon_series=True,
                                     plane_segmentation=True)
        
    def create_two_photon_series(self, metadata=None, imaging_plane=None):
        if imaging_plane is None:
            if self.nwbfile.imaging_planes:
                imaging_plane = self.nwbfile.imaging_planes[list(self.nwbfile.imaging_planes.keys())[0]]
            else:
                imaging_plane = self.add_imaging_plane()

        input_kwargs = dict(
            name='TwoPhotonSeries',
            description='no description',
            imaging_plane = self.nwbfile.imaging_planes[list(self.nwbfile.imaging_planes.keys())[0]],
            external_file=[self.segext_obj.get_movie_location()],
            format='external',
            rate=self.segext_obj.get_sampling_frequency(),
            starting_time=0.0,
            starting_frame=[0]
        )

        if metadata is None and 'Ophys' in self.metadata and 'TwoPhotonSeries' in self.metadata['Ophys']:
            metadata = self.metadata['Ophys']['TwoPhotonSeries']
            if len(metadata['imaging_planes'])>0:
                metadata['imaging_planes'] = self.nwbfile.get_imaging_plane(name=metadata['imaging_planes'])
            else:
                metadata['imaging_planes'] = self.nwbfile.imaging_planes[list(self.nwbfile.imaging_planes.keys())[0]]
        if metadata:
            input_kwargs.update(metadata)

        return self.nwbfile.add_acquisition(TwoPhotonSeries(**input_kwargs))

    def create_imaging_plane(self, optical_channel_list=None):
        """
        :param optical_channel_list:
        :return:
        """
        if not optical_channel_list:
            optical_channel_list = []
        channel_names = self.segext_obj.get_channel_names()
        for i in channel_names:
            optical_channel_list.append(self.create_optical_channel(dict(name=i)))
        self.imaging_plane = self.add_imaging_plane(optical_channel=optical_channel_list)

    def add_rois(self):
        for i, roiid in enumerate(self.segext_obj.roi_idx):
            self.plane_segmentation.add_roi(image_mask=self.segext_obj.get_image_masks(ROI_ids=[roiid]),
                                            pixel_mask=self.segext_obj.get_pixel_masks(ROI_ids=[roiid])[:,0:-1])

    def add_fluorescence_traces(self, metadata=None):
        """
        Create fluorescence traces for the nwbfile
        Parameters
        ----------
        metadata: list
            list of dictionaries with keys/words same as roi_response_series input arguments.
        Returns
        -------
        None
        """
        input_kwargs = dict(
            rois=self.create_roi_table_region(list(range(self.segext_obj.no_rois))),
            starting_time=0.0,
            rate=self.segext_obj.get_sampling_frequency(),
            unit='lumens'
        )
        if metadata:
            metadata_iter = metadata
            container_func = Fluorescence
        elif metadata is None and 'Ophys' in self.metadata and 'DfOverF' in self.metadata['Ophys']\
                and 'roi_response_series' in self.metadata['Ophys']['DfOverF'] \
                and len(self.metadata['Ophys']['DfOverF']['roi_response_series'])>0:
            metadata_iter = self.metadata['Ophys']['DfOverF']['roi_response_series']
            container_func = DfOverF
        elif metadata is None and 'Ophys' in self.metadata and 'Fluorescence' in self.metadata['Ophys'] \
                and 'roi_response_series' in self.metadata['Ophys']['Fluorescence'] \
                and len(self.metadata['Ophys']['Fluorescence']['roi_response_series'])>0:
            metadata_iter = self.metadata['Ophys']['Fluorescence']['roi_response_series']
            container_func = Fluorescence
        else:
            metadata_iter = [input_kwargs]
            container_func = Fluorescence

        for i in metadata_iter:
            i.update(
                {'rois': self.create_roi_table_region(list(range(self.segext_obj.no_rois)))})
        #Create the main fluorescence container
        fl = container_func()
        self.ophys_mod.add_data_interface(fl)
        roi_resp = dict()
        if isinstance(self.segext_obj.roi_response,dict):
            roi_resp = self.segext_obj.roi_response
        elif isinstance(self.segext_obj.roi_response,list):
            for j,i in enumerate(metadata_iter):
                if isinstance(self.segext_obj.roi_response,list):
                    roi_resp.update({i['name']:self.segext_obj.roi_response[j]})
        else:# if only one roi_resp_data set is provided, assume its corresponding to the first one
            roi_resp.update({metadata_iter[0]['name']: self.segext_obj.roi_response})
            metadata_iter = [metadata_iter[0]]
        #Iteratively populate fluo container with various roi_resp_series
        for i in metadata_iter:
            i.update(**input_kwargs)
            i.update(
                data=DataChunkIterator(data=iter_datasetvieww(roi_resp[i['name']]))
            )
            fl.create_roi_response_series(**i)

    def create_roi_table_region(self, rois, region_name= 'NeuronROIs'):
        return self.plane_segmentation.create_roi_table_region(region_name, region=rois)

    def run_conversion(self):
        """
        To populate the nwb file completely.
        """
        self.create_imaging_plane()
        self.create_plane_segmentation()
        self.add_rois()
        self.add_fluorescence_traces()
        self.create_two_photon_series(imaging_plane=self.nwbfile.get_imaging_plane(name=self.imaging_plane.name))


