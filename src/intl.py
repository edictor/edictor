#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, copy, gettext, locale, __builtin__

# Determine if application is a script file or frozen exe
if hasattr(sys, 'frozen'):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

# Replace with the appropriate catalog name
lang = {}
lang['en_US'] = gettext.translation('edictor', os.path.join(application_path,'locale'),
                                    languages=['en_US'], codeset='UTF-8')
lang['pt_BR'] = gettext.translation('edictor', os.path.join(application_path,'locale'),
                                    languages=['pt_BR'], codeset='UTF-8')
lang['en_US'].install()

def setLanguage():
    lang_dict = {}

    lang_dict[u"English"] = 'en_US'
    lang_dict[u"Português (brasileiro)"] = 'pt_BR'
   
    try:
        lg = lang_dict[unicode(__builtin__.cfg.get(u'Preferences', u'Language'))]
    except:
        lg = 'en_US'
        if not __builtin__.cfg.has_section(u'Preferences'):
            __builtin__.cfg.add_section(u'Preferences')
        __builtin__.cfg.set(u'Preferences', u'Language', _(u'English'))
    
    lang[lg].install()
