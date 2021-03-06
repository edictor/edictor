# -*- coding: utf-8 -*-
# generated by wxGlade 0.6.3 on Wed Jun  3 16:59:23 2009

import wx, time, __builtin__

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode

# end wxGlade

class CommentsDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: CommentsDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.sizer_71_staticbox = wx.StaticBox(self, -1, "")
        self.sizer_72_staticbox = wx.StaticBox(self, -1, _(u"Comentários feitos"))
        self.combo_box_3 = wx.ComboBox(self, -1, choices=[_("Novo")], style=wx.CB_DROPDOWN|wx.CB_DROPDOWN|wx.CB_READONLY)
        self.btn_remove = wx.BitmapButton(self, -1, wx.Bitmap(__builtin__.application_path + "/res/exclude.png",wx.BITMAP_TYPE_ANY))
        self.label_30 = wx.StaticText(self, -1, _("Autor:"))
        self.text_author = wx.TextCtrl(self, -1, "")
        self.label_32 = wx.StaticText(self, -1, _("Resumo:"))
        self.text_title = wx.TextCtrl(self, -1, "")
        self.text_comment = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.button_ok = wx.Button(self, -1, _("Ok"))
        self.button_cancel = wx.Button(self, -1, _("Cancelar"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.OnCboCommentClick, self.combo_box_3)
        self.Bind(wx.EVT_BUTTON, self.OnBtnRemoveClick, self.btn_remove)
        self.Bind(wx.EVT_BUTTON, self.OnOkButtonClick, self.button_ok)
        self.Bind(wx.EVT_BUTTON, self.OnCancelButtonClick, self.button_cancel)
        # end wxGlade
        
        self.combo_box_3.SetSelection(0)
        self.text_author.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

        self.comm_list = []

    def __set_properties(self):
        # begin wxGlade: CommentsDialog.__set_properties
        self.SetTitle(_(u"Comentários"))
        self.SetSize((349, 383))
        self.combo_box_3.SetSelection(-1)
        self.btn_remove.Enable(False)
        self.btn_remove.SetSize(self.btn_remove.GetBestSize())
        self.label_30.SetMinSize((50, 14))
        self.text_author.SetMinSize((200, 24))
        self.label_32.SetMinSize((51, 14))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: CommentsDialog.__do_layout
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_2_copy_copy_copy_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_71 = wx.StaticBoxSizer(self.sizer_71_staticbox, wx.HORIZONTAL)
        sizer_70 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_69 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_72 = wx.StaticBoxSizer(self.sizer_72_staticbox, wx.HORIZONTAL)
        sizer_72.Add(self.combo_box_3, 1, 0, 0)
        sizer_72.Add(self.btn_remove, 0, wx.LEFT, 5)
        sizer_4.Add(sizer_72, 0, wx.ALL|wx.EXPAND, 5)
        sizer_69.Add(self.label_30, 0, wx.ALIGN_CENTER_VERTICAL, 1)
        sizer_69.Add(self.text_author, 0, 0, 0)
        sizer_4.Add(sizer_69, 0, wx.ALL|wx.EXPAND, 5)
        sizer_70.Add(self.label_32, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_70.Add(self.text_title, 1, 0, 0)
        sizer_4.Add(sizer_70, 0, wx.ALL|wx.EXPAND, 5)
        sizer_71.Add(self.text_comment, 1, wx.EXPAND, 0)
        sizer_4.Add(sizer_71, 1, wx.ALL|wx.EXPAND, 5)
        sizer_2_copy_copy_copy_1.Add(self.button_ok, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_2_copy_copy_copy_1.Add(self.button_cancel, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 30)
        sizer_4.Add(sizer_2_copy_copy_copy_1, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(sizer_4)
        self.Layout()
        # end wxGlade

    def OnCboCommentClick(self, event): # wxGlade: CommentsDialog.<event_handler>
        if self.combo_box_3.GetSelection() == 0 or\
                self.combo_box_3.GetStringSelection() == _(u'Removido'):
            self.combo_box_3.SetSelection(0)
            self.text_author.Clear()
            self.text_title.Clear()
            self.text_comment.Clear()
            self.text_author.Enable(True)
            self.text_title.Enable(True)
            self.text_comment.Enable(True)
            self.btn_remove.Enable(False)
            self.text_author.SetFocus()
        else:
            self.text_author.ChangeValue(self.comm_list[self.combo_box_3.GetSelection() - 1]['author'])
            self.text_title.ChangeValue(self.comm_list[self.combo_box_3.GetSelection() - 1]['title'])
            self.text_comment.ChangeValue(self.comm_list[self.combo_box_3.GetSelection() - 1]['text'])
            self.text_author.Enable(False)
            self.text_title.Enable(False)
            self.text_comment.Enable(False)
            self.btn_remove.Enable(True)

    def OnOkButtonClick(self, event): # wxGlade: CommentsDialog.<event_handler>
        if self.text_comment.GetValue().strip() != u'':
            if self.text_author.GetValue().strip() == u'':
                wx.MessageBox(_(u'Nome do autor precisa ser informado.'), _(u'E-Dictor'))
                self.text_author.SetFocus()
                return
            
            # Comment
            comment = {}
            comment['author'] = self.text_author.GetValue()
            comment['date'] = time.strftime("%x")
            comment['title'] = self.text_title.GetValue()
            comment['text'] = self.text_comment.GetValue().replace('\n',' ').strip()
            comment['remove'] = False
            self.comm_list.append(comment)
            
        # Close window
        self.EndModal(wx.ID_OK)

    def OnCancelButtonClick(self, event): # wxGlade: CommentsDialog.<event_handler>
        self.EndModal(wx.ID_CANCEL)

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close(True)
        event.Skip()

    def setComments(self, el_id, comm_list):
        self.SetTitle(_(u'Comentários') + ' - ' + el_id)
        
        # Clears the combobox, except for the first option ("new")
        while len(self.combo_box_3.GetItems()) > 1:
            self.combo_box_3.Delete(1)
        # Insert already made comments
        for comm in comm_list:
            tt = comm['title']
            if tt == '': tt = comm['text'][0:30] + '...'
            self.combo_box_3.Append('[' + comm['date'] + '] ' + comm['author'] + ' : ' + tt)
        self.comm_list = comm_list
        
    def getComments(self):
        return self.comm_list

    def OnBtnRemoveClick(self, event): # wxGlade: CommentsDialog.<event_handler>
        if self.GetParent().YesNoMessageDialog(_(u'Confirma a remoção deste comentário?'), _(u'E-Dictor')):
            self.comm_list[self.combo_box_3.GetSelection() - 1]['remove'] = True
            self.combo_box_3.Insert(_(u'Removido'), self.combo_box_3.GetSelection() + 1)
            self.combo_box_3.Delete(self.combo_box_3.GetSelection())
            self.combo_box_3.SetSelection(0)
            self.OnCboCommentClick(None)

# end of class CommentsDialog


