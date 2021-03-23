import os
import sys
from pathlib import Path

sys.path.insert(0, Path(__file__).resolve().parents[1])

project = 'nwb-conversion-tools'
copyright = '2021, Cody Baker'
author = 'Cody Baker'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'myst_parser'
]
templates_path = ['_templates']
master_doc = 'index'
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'collapse_navigation': False,
    'navigation_depth': 6,
}

# --------------------------------------------------
# Extension configuration
# --------------------------------------------------

# Napoleon
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = False
napoleon_use_ivar = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True

# Autodoc
autoclass_content = "both"
autodoc_member_order = "bysource"
autodata_content = "both"
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'private-members': True,
    'show-inheritance': False,
    'toctree': True,
    'undoc-members': True
}
add_module_names=False

# autosummary