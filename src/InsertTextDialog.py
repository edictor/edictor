# -*- coding: utf-8 -*-
# generated by wxGlade 0.6.3 on Fri Jan 30 18:03:26 2009

import wx, intl

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade

class InsertTextDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # Set app language
        intl.setLanguage()
        # begin wxGlade: InsertTextDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.label_11 = wx.StaticText(self, -1, _("Entre com o texto a ser inserido:"))
        self.text_ctrl_3 = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.TE_LINEWRAP)
        self.radio_box_2 = wx.RadioBox(self, -1, _(u"Em relação à palavra atual, inserir o texto:"), choices=[_("Antes"), _("Depois")], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.button_1 = wx.Button(self, -1, _("Inserir"))
        self.button_2 = wx.Button(self, -1, _("Cancelar"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_RADIOBOX, self.OnRadioClick, self.radio_box_2)
        self.Bind(wx.EVT_BUTTON, self.OnInsertBtnClick, self.button_1)
        self.Bind(wx.EVT_BUTTON, self.OnCancelBtnClick, self.button_2)
        # end wxGlade
        
        self.text_ctrl_3.SetFocus()
        self.rb_text = ['','']

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close(True)
        event.Skip()

    def __set_properties(self):
        # begin wxGlade: InsertTextDialog.__set_properties
        self.SetTitle(_("Inserir texto"))
        self.SetSize((500, 300))
        self.label_11.SetMinSize((486, 14))
        self.text_ctrl_3.SetMinSize((490, 197))
        self.radio_box_2.SetMinSize((490, 40))
        self.radio_box_2.SetSelection(0)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: InsertTextDialog.__do_layout
        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(self.label_11, 0, wx.ALL|wx.EXPAND, 5)
        sizer_10.Add(self.text_ctrl_3, 5, wx.LEFT|wx.RIGHT|wx.EXPAND, 5)
        sizer_10.Add(self.radio_box_2, 1, wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_11.Add(self.button_1, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_11.Add(self.button_2, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_10.Add(sizer_11, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_10)
        self.Layout()
        # end wxGlade

    def OnInsertBtnClick(self, event): # wxGlade: InsertTextDialog.<event_handler>
        if self.text_ctrl_3.GetValue().strip() == '':
            wx.MessageBox(_(u'Nenhum texto informado.'),'E-Dictor')
            return
        # Close window
        self.EndModal(wx.ID_OK)

    def OnCancelBtnClick(self, event): # wxGlade: InsertTextDialog.<event_handler>
        self.EndModal(wx.ID_CANCEL)
    
    def getEnteredText(self):
        return self.text_ctrl_3.GetValue()

    def getRadioSelection(self):
        '''
        0 - Text insertion BEFORE current word
        1 - Text insertino AFTER current word
        '''
        return self.radio_box_2.GetSelection()
    
    def setRadioButtonsLabel(self, lb0, lb1, lb2):
        '''
        Change labels of radio buttons to adapt specific needs.
        '''
        self.radio_box_2.SetLabel(lb0)
        self.radio_box_2.SetItemLabel(0,lb1)
        self.radio_box_2.SetItemLabel(1,lb2)

        # Reorganize window elements
        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(self.radio_box_2, 1, wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_10.Add(self.label_11, 0, wx.ALL|wx.EXPAND, 5)
        sizer_10.Add(self.text_ctrl_3, 5, wx.LEFT|wx.RIGHT|wx.EXPAND, 5)
        sizer_11.Add(self.button_1, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_11.Add(self.button_2, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_10.Add(sizer_11, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_10)
        self.Layout()

    def setRadioButtonsBoundText(self, rb1='', rb2=''):
        '''
        Set initial text for header/footer.
        '''
        self.rb_text = [rb1, rb2]
        self.OnRadioClick(None)
        
    def OnRadioClick(self, event): # wxGlade: InsertTextDialog.<event_handler>
        '''
        Change the text in the TextBox on each RadioButton click.
        '''
        if self.radio_box_2.GetItemLabel(0) != _(u'Antes'):
            if self.text_ctrl_3.GetValue().strip() != '':
                self.rb_text[self.radio_box_2.GetSelection()-1] = self.text_ctrl_3.GetValue().strip() 
            self.text_ctrl_3.ChangeValue(self.rb_text[self.radio_box_2.GetSelection()])

# end of class InsertTextDialog


