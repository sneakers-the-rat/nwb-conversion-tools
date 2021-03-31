from nwb_conversion_tools.spec.base_spec import BaseSpec
from nwb_conversion_tools.spec.path import Path
from nwb_conversion_tools.spec.external_file import JSON


def parse_nested_spec(spec, base_dir):
    out_dict = {}
    for key, value in spec.items():
        if isinstance(value, dict):
            out_dict[key].update(parse_nested_spec(value, base_dir))
        elif issubclass(value, BaseSpec):
            out_dict[key] = value.parse(base_dir)
        else:
            out_dict[key] = value

    return out_dict
