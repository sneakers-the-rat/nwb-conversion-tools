import typing


from nwb_conversion_tools.interfaces.base_data import BaseDataInterface
from nwb_conversion_tools.interfaces import imaging, interface_utils, recording, segmentation, sorting
from nwb_conversion_tools.utils import _recursive_import, _recurse_subclasses


def list_interfaces(interface_type: typing.Optional[str] = None,
                    device_name: typing.Optional[str] = None) -> typing.Union[typing.List[typing.Type[BaseDataInterface]], BaseDataInterface]:
    """
    List all available data interfaces as a flat list, disregarding extractor subtype

    Imports modules within :mod:`nwb_conversion_tools.interfaces` (or sub-module, if interface_type is provided)
    and lists __subclasses__ of :class:`.interfaces.BaseDataInterface` recursively.

    Args:
        interface_type (None, str): if None, list all interfaces. Otherwise, if some interface
            subtype if provided (eg. ``'imaging'``, ``'recording'``), only list interfaces of that type.
        device_name (None, str): If None, list all interfaces (or of a type if ``interface_type``
            is not ``None``), if specified, return a device

    Returns:
        list: list of data interfaces inheriting from :class:`.interfaces.BaseDataInterface`,
            or if ``device_name`` is not None, the DataInterface object itself

    Examples:

        List all interfaces::

            all_interfaces = list_interfaces()

        List all recording interfaces::

            recording_interfaces = list_interfaces('recording')

        Get a specific recording interface::

            open_ephys_interface = list_interfaces('recording', 'open_ephys')
    """

    # recursively import all submodules in interfaces so they're in sys.modules
    import_module = "nwb_conversion_tools.interfaces"
    if interface_type is not None:
        import_module = '.'.join([import_module, interface_type])

    _recursive_import(import_module)
    subclasses = _recurse_subclasses(BaseDataInterface)

    if interface_type is not None:
        subclasses = [interface for interface in subclasses if interface.interface_type == interface_type]

    if device_name is not None:
        # do a super ugly iteration through subclasses to find one with a matching device_name
        ret_interface = [interface for interface in subclasses if interface.device_name == device_name]
        if len(ret_interface) > 1:
            raise NameError(f'device_name was specified, but got multiple matching interfaces. likely missing interface_type, got interface_type: {interface_type} and device_name: {device_name}')
        elif len(ret_interface) < 1:
            raise NameError(f'no matching device_name could be found. got interface_type: {interface_type} and device_name: {device_name}')
        else:
            return ret_interface[0]

    else:
        return subclasses

