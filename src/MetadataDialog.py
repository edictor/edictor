# -*- coding: utf-8 -*-
# generated by wxGlade 0.6.3 on Thu Feb 19 18:03:00 2009

import wx, intl, __builtin__

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade

class MetadataDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # Set app language
        intl.setLanguage()
        # begin wxGlade: MetadataDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.sizer_40_staticbox = wx.StaticBox(self, -1, _("Metadado"))
        self.label_12 = wx.StaticText(self, -1, _("Tipo:"))
        self.combo_box_1 = wx.ComboBox(self, -1, choices=[], style=wx.CB_DROPDOWN|wx.CB_DROPDOWN|wx.CB_READONLY|wx.CB_SORT)
        self.label_13 = wx.StaticText(self, -1, _("Nome:"))
        self.combo_box_2 = wx.ComboBox(self, -1, choices=[], style=wx.CB_DROPDOWN|wx.CB_DROPDOWN|wx.CB_READONLY|wx.CB_SORT)
        self.label_14 = wx.StaticText(self, -1, _("Valor:"))
        self.text_ctrl_5 = wx.TextCtrl(self, -1, "")
        self.list_box_1 = wx.ListBox(self, -1, choices=[], style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_SORT)
        self.button_4 = wx.Button(self, -1, _("<<"))
        self.button_3 = wx.Button(self, -1, _("Remover"))
        self.button_ok = wx.Button(self, -1, _("Ok"))
        self.button_cancel = wx.Button(self, -1, _("Cancelar"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.OnGenerationClick, self.combo_box_1)
        self.Bind(wx.EVT_COMBOBOX, self.OnMetaNameClick, self.combo_box_2)
        self.Bind(wx.EVT_LISTBOX, self.OnListMetadataClick, self.list_box_1)
        self.Bind(wx.EVT_BUTTON, self.OnAddMeta, self.button_4)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveMeta, self.button_3)
        self.Bind(wx.EVT_BUTTON, self.OnOkButtonClick, self.button_ok)
        self.Bind(wx.EVT_BUTTON, self.OnCancelButtonClick, self.button_cancel)
        # end wxGlade
        
        self.metadata = None
        self.meta_names = {}
        for meta_info in __builtin__.cfg.get(u'Preferences', u'Metadata').decode('utf-8').split(','):
            (type, name) = meta_info.split(' | ')
            if not type in self.meta_names: self.meta_names[type] = []
            self.meta_names[type].append(name)

        self.combo_box_1.SetItems(self.meta_names.keys())
        self.combo_box_1.SetFocus()

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close(True)
        event.Skip()

    def __set_properties(self):
        # begin wxGlade: MetadataDialog.__set_properties
        self.SetTitle(_("Metadados"))
        self.SetSize((558, 408))
        self.label_12.SetMinSize((45, 14))
        self.label_13.SetMinSize((45, 14))
        self.combo_box_2.SetMinSize((250, 27))
        self.label_14.SetMinSize((45, 14))
        self.text_ctrl_5.SetMinSize((490, 24))
        self.button_3.Enable(False)
        # end wxGlade
   
    def __do_layout(self):
        # begin wxGlade: MetadataDialog.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_2_copy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_38 = wx.BoxSizer(wx.VERTICAL)
        sizer_43 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_44 = wx.BoxSizer(wx.VERTICAL)
        sizer_40 = wx.StaticBoxSizer(self.sizer_40_staticbox, wx.VERTICAL)
        sizer_42 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_41 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_39 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_39.Add(self.label_12, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_39.Add(self.combo_box_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_40.Add(sizer_39, 0, wx.ALL, 2)
        sizer_41.Add(self.label_13, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_41.Add(self.combo_box_2, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_40.Add(sizer_41, 1, wx.EXPAND, 0)
        sizer_42.Add(self.label_14, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_42.Add(self.text_ctrl_5, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_40.Add(sizer_42, 1, wx.EXPAND, 0)
        sizer_38.Add(sizer_40, 0, wx.LEFT|wx.RIGHT|wx.EXPAND, 5)
        sizer_43.Add(self.list_box_1, 1, wx.LEFT|wx.TOP|wx.EXPAND, 5)
        sizer_44.Add(self.button_4, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer_44.Add(self.button_3, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 2)
        sizer_43.Add(sizer_44, 0, wx.TOP|wx.EXPAND, 5)
        sizer_38.Add(sizer_43, 1, wx.EXPAND, 0)
        sizer_8.Add(sizer_38, 1, wx.EXPAND, 0)
        sizer_2_copy.Add(self.button_ok, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_2_copy.Add(self.button_cancel, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_8.Add(sizer_2_copy, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 10)
        self.SetSizer(sizer_8)
        self.Layout()
        # end wxGlade

    def OnListMetadataClick(self, event): # wxGlade: MetadataDialog.<event_handler>
        if self.list_box_1.GetSelection() != wx.NOT_FOUND:
            self.button_3.Enable(True)
            # Show values in the form fields
            i = self.combo_box_2.FindString(self.list_box_1.GetStringSelection().split(' ] ')[0][2:])
            if i != wx.NOT_FOUND:
                self.combo_box_2.SetSelection(i)
            else:
                self.combo_box_2.SetValue(self.list_box_1.GetStringSelection().split(' ] ')[0][2:])
            self.text_ctrl_5.ChangeValue(self.list_box_1.GetStringSelection().split(' ] ')[1])
            self.text_ctrl_5.SetFocus()

    def OnOkButtonClick(self, event): # wxGlade: MetadataDialog.<event_handler>
        # Close window
        self.EndModal(wx.ID_OK)

    def OnCancelButtonClick(self, event): # wxGlade: MetadataDialog.<event_handler>
        self.EndModal(wx.ID_CANCEL)
        
    def getMetadata(self):
        '''
        Process form contents and generate a dictionary with
        metadata information.
        '''
        return self.metadata
    
    def setMetadata(self, metadata):
        '''
        Load the metadata information.
        '''
        self.metadata = metadata.copy()

    def OnGenerationClick(self, event): # wxGlade: MetadataDialog.<event_handler>
        self.list_box_1.Clear()
        self.combo_box_2.Clear()
        if self.combo_box_1.GetStringSelection().strip() != '':
            key = self.combo_box_1.GetStringSelection()
            if key in self.metadata:
                # Shows values already set for metadata generation fields
                for meta in self.metadata[key]:
                    self.list_box_1.Append(u'[ '+meta[0]+' ] '+meta[1])
            else:
                self.metadata[key] = []

            # Metadata generation field names
            for name in self.meta_names[key]:
                self.combo_box_2.Append(name)
        # Reset fields
        self.text_ctrl_5.Clear()
        self.combo_box_2.SetSelection(wx.NOT_FOUND)
        self.combo_box_2.SetValue('')
            
    def OnAddMeta(self, event): # wxGlade: MetadataDialog.<event_handler>
        if self.combo_box_2.GetValue().strip() == '':
            wx.MessageBox(_(u'É necessário escolher algum metadado.'),_('E-Dictor'))
            self.combo_box_2.SetFocus()
            return
        if self.text_ctrl_5.GetValue().strip() == '':
            wx.MessageBox(_(u'É necessário informar um valor para o metadado.'),'E-Dictor')
            self.text_ctrl_5.SetFocus()
            return
        # Remove preexistent metadata from the listbox
        for m in self.list_box_1.GetStrings():
            if m.find(u'[ '+self.combo_box_2.GetValue().strip()+' ]') >= 0:
                self.list_box_1.SetStringSelection(m)
                self.list_box_1.Delete(self.list_box_1.GetSelection())
                break
        # Update metadata dictionary
        for meta in self.metadata[self.combo_box_1.GetStringSelection()]:
            if meta[0] == self.combo_box_2.GetValue().strip():
                self.metadata[self.combo_box_1.GetStringSelection()].remove(meta)
                break
        meta = (self.combo_box_2.GetValue().strip(),self.text_ctrl_5.GetValue().strip())
        self.metadata[self.combo_box_1.GetStringSelection()].append(meta)
        # Insert metadata
        self.list_box_1.Append(u'[ '+meta[0]+' ] '+meta[1])
        # Reset fields
        self.text_ctrl_5.Clear()
        self.combo_box_2.SetSelection(wx.NOT_FOUND)
        self.combo_box_2.SetValue('')
        self.combo_box_2.SetFocus()
        self.button_3.Enable(False)

    def OnRemoveMeta(self, event): # wxGlade: MetadataDialog.<event_handler>
        if self.list_box_1.GetSelection() != wx.NOT_FOUND:
            # Update metadata dictionary
            for meta in self.metadata[self.combo_box_1.GetStringSelection()]:
                if meta[0] == self.list_box_1.GetStringSelection().split(' ] ')[0][2:]:
                    self.metadata[self.combo_box_1.GetStringSelection()].remove(meta)
                    break
            # Remove from listbox
            self.list_box_1.Delete(self.list_box_1.GetSelection())
            self.list_box_1.SetSelection(wx.NOT_FOUND)
            self.button_3.Enable(False)
            # Reset fields
            self.text_ctrl_5.Clear()
            self.combo_box_2.SetSelection(wx.NOT_FOUND)
            self.combo_box_2.SetValue('')
            self.combo_box_2.SetFocus()

    def OnMetaNameClick(self, event): # wxGlade: MetadataDialog.<event_handler>
        # Get metadata value (if any)
        for m in self.list_box_1.GetStrings():
            if m.find(u'[ '+self.combo_box_2.GetValue().strip()+' ]') >= 0:
                self.text_ctrl_5.ChangeValue(m.split(' ] ')[1])
                break
        self.text_ctrl_5.SetFocus()

# end of class MetadataDialog

