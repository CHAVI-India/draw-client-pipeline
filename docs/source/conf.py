# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DRAW Client'
copyright = '2025, Tata Medical Center, Kolkata'
author = 'Dr Santam Chakraborty'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosectionlabel',
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'insipid'

# # docs/source/conf.py (see https://www.bomberbot.com/python/documenting-your-django-project-with-sphinx-a-comprehensive-guide/)

# import os
# import sys
# import django

# sys.path.insert(0, os.path.abspath('../..'))  # Assuming conf.py is in docs/source/
# os.environ['DJANGO_SETTINGS_MODULE'] = 'draw_client.settings'
# django.setup()