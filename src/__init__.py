# -*- coding: utf-8 -*-
# EDictor
#
# Copyright (C) 2009 Pablo Faria
#
# Portions of copyright to Fábil N. Kepler, Maria Clara P. de Souza
#
# Authors: Pablo Faria <pablofaria@gmail.com>
#          Fábio N. Kepler <kepler@ime.usp.br>
#          Maria Clara P. de Souza <mariaclara.ps@gmail.com>
#
# URL:     https://oncoto.dyndns.org:44883/projects/edictor/
#
# For license information, see COPYING.

"""
EDictor is an integrated tool for annotating and editing of corpora

@version: 1.0.b008
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

__product_name__ = "EDictor"

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "1.0.b008"

# Copyright notice
__copyright__ = """\
Copyright (C) 2013 Pablo Faria

Portions of copyright to Fábio N. Kepler, Maria Clara P. de Souza

Distributed and Licensed under provisions of the MIT
License, which is included by reference.
"""

__license__ = "GNU Public License v3 or higher"

# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
EDictor is a Python tool for annotating and editing corpora, in the
format used by the Tycho Brahe corpora (http://www.tycho.iel.unicamp.br/~tycho).
EDictor has been tested with Python 2.5, wxPython 2.8, and lxml 1.3.3."""

__keywords__ = ['corpora','corpus','annotation','corpus annotation','corpora annotation',
                'linguistics', 'language']

__url__ = "http://github.com/edictor/edictor"

# Maintainer, contributors, etc.
__maintainer__ = "Fabio N. Kepler, Pablo Faria"
__maintainer_email__ = "fabio@kepler.pro.br, pablofaria@gmail.com"
__author__ = __maintainer__ + " and Maria Clara P. Souza"
__author_email__ = __maintainer_email__ + ", mariaclara.ps@gmail.com"
__company_name__ = "IME-USP, IEL-Unicamp"

# Import top-level utilities into top-level namespace

from edictor import *
from Graphy import *
from MainFrame import *
from InsertBreakDialog import InsertBreakDialog 
from InsertTextDialog import InsertTextDialog 
from ElementPropertiesDialog import ElementPropertiesDialog 
from TextPropertiesDialog import TextPropertiesDialog 
from MetadataDialog import MetadataDialog 
from FindReplaceDialog import FindReplaceDialog 
from EditionReplaceDialog import EditionReplaceDialog 
from PreferencesDialog import PreferencesDialog 
from CommentsDialog import CommentsDialog 
from AboutDialog import AboutDialog 
from TestUnits import Test
from TextCtrlAutoComplete import TextCtrlAutoComplete 

# Processing packages -- these all define __all__ carefully.
from contrib_nltk import *

