# -*- coding: utf-8 -*-
# generated by wxGlade 0.6.3 on Tue May  5 11:26:52 2009

import wx, re, string

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade

class FindReplaceDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: FindReplaceDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.sizer_56_staticbox = wx.StaticBox(self, -1, _(u"Opções"))
        self.label_21 = wx.StaticText(self, -1, _("Procurar:"))
        self.cb_find = wx.ComboBox(self, -1, choices=[], style=wx.CB_DROPDOWN)
        self.label_22 = wx.StaticText(self, -1, _("Substituir:"))
        self.cb_replace = wx.ComboBox(self, -1, choices=[], style=wx.CB_DROPDOWN)
        self.chk_case = wx.CheckBox(self, -1, _(u"Sensível à caixa"))
        self.chk_backwards = wx.CheckBox(self, -1, _(u"Para trás"))
        self.chk_whole = wx.CheckBox(self, -1, _("Palavra inteira"))
        self.chk_ortext = wx.CheckBox(self, -1, _("Texto original apenas"))
        self.chk_confirm = wx.CheckBox(self, -1, _(u"Confirmar substituição"))
        self.chk_edtext = wx.CheckBox(self, -1, _("Texto editado"))
        self.chk_fromcursor = wx.CheckBox(self, -1, _("Do cursor em diante"))
        self.btn_find = wx.Button(self, -1, _("Procurar"))
        self.btn_cancel = wx.Button(self, -1, _("Cancelar"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT_ENTER, self.OnFindEnter, self.cb_find)
        self.Bind(wx.EVT_TEXT, self.OnFTextEnter, self.cb_find)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnReplaceEnter, self.cb_replace)
        self.Bind(wx.EVT_TEXT, self.OnRTextEnter, self.cb_replace)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckOrText, self.chk_ortext)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckEdText, self.chk_edtext)
        self.Bind(wx.EVT_BUTTON, self.OnOkButtonClick, self.btn_find)
        self.Bind(wx.EVT_BUTTON, self.OnCancelButtonClick, self.btn_cancel)
        # end wxGlade

        self.Bind(wx.EVT_SHOW, self.OnShow)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        
        self.main_window_ref = None
        self.found = False
        self.sel_i = 0
        self.sel_f = 0
        
        # These variables will hold the older entries in the dialog
        self.search_strings = []
        self.replace_strings = []

    def __set_properties(self):
        # begin wxGlade: FindReplaceDialog.__set_properties
        self.SetTitle(_("Procurar/Substituir"))
        self.label_21.SetMinSize((80, 14))
        self.cb_find.SetFocus()
        self.label_22.SetMinSize((80, 14))
        self.cb_replace.Enable(False)
        self.chk_case.SetValue(1)
        self.chk_ortext.Enable(False)
        self.chk_ortext.SetValue(1)
        self.chk_confirm.Enable(False)
        self.chk_confirm.SetValue(1)
        self.chk_edtext.Enable(False)
        self.chk_fromcursor.SetValue(1)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: FindReplaceDialog.__do_layout
        sizer_46 = wx.BoxSizer(wx.VERTICAL)
        sizer_2_copy_copy_copy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_56 = wx.StaticBoxSizer(self.sizer_56_staticbox, wx.HORIZONTAL)
        grid_sizer_2 = wx.GridSizer(4, 2, 2, 2)
        sizer_47 = wx.BoxSizer(wx.VERTICAL)
        sizer_58 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_57 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_57.Add(self.label_21, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_57.Add(self.cb_find, 0, wx.ALL|wx.EXPAND, 4)
        sizer_47.Add(sizer_57, 1, wx.EXPAND, 0)
        sizer_58.Add(self.label_22, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_58.Add(self.cb_replace, 0, wx.ALL|wx.EXPAND, 4)
        sizer_47.Add(sizer_58, 1, wx.EXPAND, 0)
        sizer_46.Add(sizer_47, 0, wx.ALL|wx.EXPAND, 4)
        grid_sizer_2.Add(self.chk_case, 0, 0, 0)
        grid_sizer_2.Add(self.chk_backwards, 0, 0, 0)
        grid_sizer_2.Add(self.chk_whole, 0, 0, 3)
        grid_sizer_2.Add(self.chk_ortext, 0, 0, 0)
        grid_sizer_2.Add(self.chk_confirm, 0, 0, 0)
        grid_sizer_2.Add(self.chk_edtext, 0, 0, 0)
        grid_sizer_2.Add(self.chk_fromcursor, 0, 0, 0)
        sizer_56.Add(grid_sizer_2, 1, wx.EXPAND, 0)
        sizer_46.Add(sizer_56, 1, wx.ALL|wx.EXPAND, 4)
        sizer_2_copy_copy_copy.Add(self.btn_find, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_2_copy_copy_copy.Add(self.btn_cancel, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_46.Add(sizer_2_copy_copy_copy, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 10)
        self.SetSizer(sizer_46)
        sizer_46.Fit(self)
        self.Layout()
        # end wxGlade

    def OnShow(self, event):
        self.main_window_ref.SetStatusBarMessage(u'')
        self.cb_find.SetFocus()
        self.MoveXY(self.main_window_ref.GetSizeTuple()[0] - self.GetSizeTuple()[0],
                    self.main_window_ref.GetSizeTuple()[1] - self.GetSizeTuple()[1])
        
    def OnClose(self, event):
        """
        Handles the user clicking the window/dialog "close" button/icon.
        """
        if len(self.cb_replace.GetValue().strip()) == 0:
            self.main_window_ref.text_ctrl_ocr.SetSelection(self.sel_i, self.sel_f)
        else:
            self.main_window_ref.text_ctrl_ocr.ShowPosition(self.sel_i)
        event.Skip()

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close(True)
        event.Skip()

    def OnOkButtonClick(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        if len(self.cb_find.GetValue().strip()) > 0:
            if self.chk_backwards.GetValue():
                self.findPrevious()
            else:
                self.findNext()
            if len(self.cb_replace.GetValue().strip()) > 0:
                while self.found:
                    if self.replace():
                        if self.chk_backwards.GetValue():
                            self.findPrevious()
                        else:
                            self.findNext()
                    else:
                        # User choosed CANCEL
                        break
                self.main_window_ref.text_ctrl_ocr.SetSelection(0,0)

    def OnCancelButtonClick(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        self.Close(True)
        
    def getSearchString(self):
        return self.cb_find.GetValue()
        
    def configureDialog(self, main_window):
        '''
        Configure dialog based on main_window state.
        '''
        # Keeps main window reference
        self.main_window_ref = main_window
        
        # Enable Replace for simple text
        self.cb_replace.Enable(main_window.graphy is None)
        
        # Simple text options
        self.chk_confirm.Enable(main_window.graphy is None)

        # Options for the XML text
        self.chk_ortext.Enable(main_window.graphy is not None)
        self.chk_edtext.Enable(main_window.graphy is not None)
        
        # Load ComboBoxes with older searches
        self.cb_find.Clear()
        self.cb_replace.Clear()
        self.cb_find.AppendItems(self.search_strings)
        self.cb_replace.AppendItems(self.replace_strings)
    
    def findNext(self):
        search_str = self.cb_find.GetValue()
        
        # Remember this search later
        if search_str not in self.search_strings:
            self.search_strings.insert(0, search_str)
            self.cb_find.Insert(search_str, 0)

        # Case sensitiveness
        if not self.chk_case.GetValue():
            search_str = search_str.lower()

        if self.main_window_ref.graphy is None:
            # "Whole word" search (optional)
            if self.chk_whole.GetValue() and search_str not in string.punctuation:
                search_str = r'\b'+search_str+r'\b'

            self.main_window_ref.notebook_1.ChangeSelection(0)
            target_str = self.main_window_ref.text_ctrl_ocr.GetValue()
            if not self.chk_case.GetValue():
                target_str = target_str.lower()
            pos = 0
            if self.chk_fromcursor.GetValue():
                pos = self.main_window_ref.text_ctrl_ocr.GetSelection()[0]
            if len(self.main_window_ref.text_ctrl_ocr.GetStringSelection()) > 0:
                pos = self.main_window_ref.text_ctrl_ocr.GetSelection()[0] + 1
            for m in re.finditer(search_str,target_str[pos:]):
                s_str = m.group(0)
                self.main_window_ref.text_ctrl_ocr.SetSelection(pos + m.start(), pos + m.end())
                self.main_window_ref.text_ctrl_ocr.ShowPosition(pos + m.start())
                self.sel_i = pos + m.start()
                self.sel_f = pos + m.end()
                self.found = True
                return True

            # Check for no occurrences at all
            try:
                re.finditer(search_str,target_str).next()
            except:
                wx.MessageBox(_(u'Nenhuma ocorrência.'), _(u'E-Dictor'))
                self.found = False
                return False
            
            # Check for end of document
            if self.main_window_ref.YesNoMessageDialog(_(u'Chegou ao fim do documento. Recomeça?'),_(u'E-Dictor')):
                pos = 0
                for m in re.finditer(search_str,target_str[pos:]):
                    s_str = m.group(0)
                    self.main_window_ref.text_ctrl_ocr.SetSelection(pos + m.start(), pos + m.end())
                    self.main_window_ref.text_ctrl_ocr.ShowPosition(pos + m.start())
                    self.sel_i = pos + m.start()
                    self.sel_f = pos + m.end()
                    self.found = True
                    return True
        else:
            self.main_window_ref.notebook_1.ChangeSelection(1)
            tmp_list = self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordsList()
            pos = 0
            if self.chk_fromcursor.GetValue():
                if self.main_window_ref.graphy_word_editing is not None: 
                    pos = tmp_list.index(self.main_window_ref.graphy_word_editing) + 1
            for ii in range(pos,len(tmp_list)):
                w_obj = tmp_list[ii]
                if self.chk_edtext.GetValue(): 
                    target = w_obj.getString().replace("_"," ")
                else:
                    target = w_obj.getOriginalString().replace("_"," ")
                blank_spcs = search_str.count(' ') - target.count(' ')
                kk = 1
                while (blank_spcs > 0 and len(tmp_list) > (ii+kk)):
                    if self.chk_edtext.GetValue(): 
                        target += ' ' + tmp_list[ii+kk].getString().replace("_"," ")
                    else:
                        target += ' ' + tmp_list[ii+kk].getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk += 1
                if not self.chk_case.GetValue():
                    target = target.lower()
                if (self.chk_whole.GetValue() and target == search_str) or\
                        (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                    self.main_window_ref.graphy_word_editing = w_obj
                    if self.main_window_ref.GetCurrentPageNumber() != self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj):
                        self.main_window_ref.GoToPageNumber(self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj))
                    self.main_window_ref.turnOnEdition()
                    self.found = True
                    return True

            # Check for no occurrences at all
            try:
                aux = False
                for ii in range(len(tmp_list)):
                    w_obj = tmp_list[ii]
                    if self.chk_edtext.GetValue(): 
                        target = w_obj.getString().replace("_"," ")
                    else:
                        target = w_obj.getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk = 1
                    while (blank_spcs > 0 and len(tmp_list) > (ii+kk)):
                        if self.chk_edtext.GetValue(): 
                            target += ' ' + tmp_list[ii+kk].getString().replace("_"," ")
                        else:
                            target += ' ' + tmp_list[ii+kk].getOriginalString().replace("_"," ")
                        blank_spcs = search_str.count(' ') - target.count(' ')
                        kk += 1
                    if not self.chk_case.GetValue():
                        target = target.lower()
                    if (self.chk_whole.GetValue() and target == search_str) or\
                            (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                        aux = True
                        break
                if not aux: raise
            except:
                wx.MessageBox(_(u'Nenhuma ocorrência.'), _(u'E-Dictor'))
                self.found = False
                return False
            
            # Check for end of document
            if self.main_window_ref.YesNoMessageDialog(_(u'Chegou ao fim do documento. Recomeça?'),_(u'E-Dictor')):
                pos = 0
                for ii in range(pos,len(tmp_list)):
                    w_obj = tmp_list[ii]
                    if self.chk_edtext.GetValue(): 
                        target = w_obj.getString().replace("_"," ")
                    else:
                        target = w_obj.getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk = 1
                    while (blank_spcs > 0 and len(tmp_list) > (ii+kk)):
                        if self.chk_edtext.GetValue(): 
                            target += ' ' + tmp_list[ii+kk].getString().replace("_"," ")
                        else:
                            target += ' ' + tmp_list[ii+kk].getOriginalString().replace("_"," ")
                        blank_spcs = search_str.count(' ') - target.count(' ')
                        kk += 1
                    if not self.chk_case.GetValue():
                        target = target.lower()
                    if (self.chk_whole.GetValue() and target == search_str) or\
                            (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                        self.main_window_ref.graphy_word_editing = w_obj
                        if self.main_window_ref.GetCurrentPageNumber() != self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj):
                            self.main_window_ref.GoToPageNumber(self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj))
                        self.main_window_ref.turnOnEdition()
                        self.found = True
                        return True

        self.found = False
        self.sel_i = 0
        self.sel_f = 0
        return False

    def findPrevious(self):
        search_str = self.cb_find.GetValue()
        
        # Remember this search later
        if search_str not in self.search_strings:
            self.search_strings.insert(0, search_str)
            self.cb_find.Insert(search_str, 0)

        # Case sensitiveness
        if not self.chk_case.GetValue():
            search_str = search_str.lower()

        if self.main_window_ref.graphy is None:
            # "Whole word" search (optional)
            if self.chk_whole.GetValue() and search_str not in string.punctuation:
                search_str = r'\b'+search_str+r'\b'

            self.main_window_ref.notebook_1.ChangeSelection(0)
            target_str = self.main_window_ref.text_ctrl_ocr.GetValue()
            if not self.chk_case.GetValue():
                target_str = target_str.lower()
            pos = 0
            if self.chk_fromcursor.GetValue():
                pos = self.main_window_ref.text_ctrl_ocr.GetSelection()[0]
            if len(self.main_window_ref.text_ctrl_ocr.GetStringSelection()) > 0:
                pos = self.main_window_ref.text_ctrl_ocr.GetSelection()[0]
            m = None
            for m in re.finditer(search_str,target_str[0:pos]):
                pass
            if m is not None:
                s_str = m.group(0)
                self.main_window_ref.text_ctrl_ocr.SetSelection(m.start(), m.end())
                self.main_window_ref.text_ctrl_ocr.ShowPosition(m.start())
                self.sel_i = m.start()
                self.sel_f = m.end()
                self.found = True
                return True
            else:
                # Check for no occurrences at all
                try:
                    re.finditer(search_str,target_str).next()
                except:
                    wx.MessageBox(_(u'Nenhuma ocorrência.'), _(u'E-Dictor'))
                    self.found = False
                    return False
                
                # Check for end of document
                if self.main_window_ref.YesNoMessageDialog(_(u'Chegou ao início do documento. Recomeça do fim?'),_(u'E-Dictor')):
                    m = None
                    for m in re.finditer(search_str,target_str):
                        pass
                    if m is not None:
                        s_str = m.group(0)
                        self.main_window_ref.text_ctrl_ocr.SetSelection(m.start(), m.end())
                        self.main_window_ref.text_ctrl_ocr.ShowPosition(m.start())
                        self.sel_i = m.start()
                        self.sel_f = m.end()
                        self.found = True
                        return True
        else:
            self.main_window_ref.notebook_1.ChangeSelection(1)
            tmp_list = self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordsList()
            pos = 0
            if self.chk_fromcursor.GetValue():
                if self.main_window_ref.graphy_word_editing is not None: 
                    pos = tmp_list.index(self.main_window_ref.graphy_word_editing) - 1
            for pos in range(pos,0,-1):
                w_obj = tmp_list[pos]
                if self.chk_edtext.GetValue(): 
                    target = w_obj.getString().replace("_"," ")
                else:
                    target = w_obj.getOriginalString().replace("_"," ")
                blank_spcs = search_str.count(' ') - target.count(' ')
                kk = 1
                while (blank_spcs > 0 and len(tmp_list) > (pos+kk)):
                    if self.chk_edtext.GetValue(): 
                        target += ' ' + tmp_list[pos+kk].getString().replace("_"," ")
                    else:
                        target += ' ' + tmp_list[pos+kk].getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk += 1
                if not self.chk_case.GetValue():
                    target = target.lower()
                if (self.chk_whole.GetValue() and target == search_str) or\
                        (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                    self.main_window_ref.graphy_word_editing = w_obj
                    if self.main_window_ref.GetCurrentPageNumber() != self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj):
                        self.main_window_ref.GoToPageNumber(self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj))
                    self.main_window_ref.turnOnEdition()
                    self.found = True
                    return True

            # Check for no occurrences at all
            try:
                aux = False
                for ii in range(len(tmp_list)):
                    w_obj = tmp_list[ii]
                    if self.chk_edtext.GetValue(): 
                        target = w_obj.getString().replace("_"," ")
                    else:
                        target = w_obj.getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk = 1
                    while (blank_spcs > 0 and len(tmp_list) > (ii+kk)):
                        if self.chk_edtext.GetValue(): 
                            target += ' ' + tmp_list[ii+kk].getString().replace("_"," ")
                        else:
                            target += ' ' + tmp_list[ii+kk].getOriginalString().replace("_"," ")
                        blank_spcs = search_str.count(' ') - target.count(' ')
                        kk += 1
                    if not self.chk_case.GetValue():
                        target = target.lower()
                    if (self.chk_whole.GetValue() and target == search_str) or\
                            (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                        aux = True
                        break
                if not aux: raise
            except:
                wx.MessageBox(_(u'Nenhuma ocorrência.'), _(u'E-Dictor'))
                self.found = False
                return False
            
            # Check for end of document
            if self.main_window_ref.YesNoMessageDialog(_(u'Chegou ao início do documento. Recomeça do fim?'),_(u'E-Dictor')):
                for pos in range(len(tmp_list) - 1,0,-1):
                    w_obj = tmp_list[pos]
                    if self.chk_edtext.GetValue(): 
                        target = w_obj.getString().replace("_"," ")
                    else:
                        target = w_obj.getOriginalString().replace("_"," ")
                    blank_spcs = search_str.count(' ') - target.count(' ')
                    kk = 1
                    while (blank_spcs > 0 and len(tmp_list) > (pos+kk)):
                        if self.chk_edtext.GetValue(): 
                            target += ' ' + tmp_list[pos+kk].getString().replace("_"," ")
                        else:
                            target += ' ' + tmp_list[pos+kk].getOriginalString().replace("_"," ")
                        blank_spcs = search_str.count(' ') - target.count(' ')
                        kk += 1
                    if not self.chk_case.GetValue():
                        target = target.lower()
                    if (self.chk_whole.GetValue() and target == search_str) or\
                            (not self.chk_whole.GetValue() and target.find(search_str) >= 0):
                        self.main_window_ref.graphy_word_editing = w_obj
                        if self.main_window_ref.GetCurrentPageNumber() != self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj):
                            self.main_window_ref.GoToPageNumber(self.main_window_ref.graphy.getTexts()[self.main_window_ref.active_text].getWordContainingPage(w_obj))
                        self.main_window_ref.turnOnEdition()
                        self.found = True
                        return True

        self.found = False
        self.sel_i = 0
        self.sel_f = 0
        return False
        
    def replace(self):
        '''
        Only available for simple text, not for XML.
        '''
        replace_str = self.cb_replace.GetValue().strip()

        cf = wx.ID_YES
        if self.chk_confirm.GetValue():
            # TODO: how to avoid hiding the selecion in MainFrame.text_ctrl_ocr?
            cf = wx.MessageDialog(self, _(u'Confirma a substituição?'), _(u'E-Dictor'),
                                  wx.YES | wx.NO | wx.CANCEL | wx.ICON_QUESTION | wx.YES_DEFAULT).ShowModal()

        if cf == wx.ID_CANCEL:
            return False

        if cf == wx.ID_YES:
            self.main_window_ref.text_ctrl_ocr.Replace(self.sel_i,self.sel_f,replace_str)

        if replace_str not in self.replace_strings:
            self.replace_strings.insert(0, replace_str)
            self.cb_replace.Insert(replace_str, 0)
            
        return True
    
    def OnFTextEnter(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        pass
    
    def OnKeyPress(self, event):
        print event.GetKeyCode()
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.OnCancelButtonClick(None)

    def OnRTextEnter(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        pass
    
    def OnFindEnter(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        self.OnOkButtonClick(None)

    def OnReplaceEnter(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        self.OnOkButtonClick(None)

    def OnCheckOrText(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        self.chk_edtext.SetValue(not self.chk_ortext.GetValue())

    def OnCheckEdText(self, event): # wxGlade: FindReplaceDialog.<event_handler>
        self.chk_ortext.SetValue(not self.chk_edtext.GetValue())

# end of class FindReplaceDialog


