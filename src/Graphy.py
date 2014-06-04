# -*- coding: utf-8 -*-

"""
Neste arquivo estão definidas as classes para processamento eletrônico dos 
textos, tanto na conversão para XML e sua manipulação, quanto para a
exportação em diferentes formatos.
"""

# Imports
import contrib_nltk.tokenize
import time,re,sys,__builtin__,intl,cgi
from lxml import etree
from StringIO import StringIO
#from xml.sax.saxutils import escape
#from xml.sax.saxutils import unescape

class XMLValidationError(BaseException):
    pass


class XMLEditingError(BaseException):
    pass

# This dictionary binds Classes to "indexing dictionaries" (used to enumerate
# the document elements)
__builtin__.el_type_dict = {'Section':'sc_dict','Paragraph':'p_dict','Sentence':'s_dict',
                            'SectionElement':'sce_dict','TextElement':'te_dict','Break':'bk_dict'}

"""
2007 XML style:
<ed_mark re="v" id="a_004_em_1">
      <ed t="exp" id="a_004_ed_1">Vossa Excelência </ed>
      <or id="a_004_or_1">V. Ex.a  </or>
</ed_mark>
"""

"""
2008 XML style:
<w id='' t='' l=''>
    <o id='' t='' fon=''>OriginalWord</o>
    <e id='' t='xxx'>EditedWord</e>
    ...
    <e id='' t='yyy'>EditedWord</e>
    <m id='' v='' t=''/> or <m id='' v='' t=''>MorfWord</m>
    <f id=''></f>
</w>
"""

class Word():
    '''
    This class wraps the subtrees of the document, included between
    <w></w> and provides specific operations over its content.
    '''
    def __init__(self, parent, node, loc, word=None):
        self.parent = parent
        self.node = node
        self.loc = loc      # Sentence 'id' expected
        self.map = dict()
        self.text = None
        self.pos_modified = False
        self.has_merge = False
        self.focus = False
        self.bold = False
        self.italic = False
        self.capitular = False
        self.underline = False
        self.comments_list = []
        self.containing_page = None
        self.lang = ''

        # Building from preexistent node
        if word is None:
            self._build(node)
        # Building from raw text (ppff: when?)
        else:
            self.node = None
            self.id = loc+'#'+str(self.getParent().getElements().index(self))
            self.text = word
    
    def _build(self, node):
        if node.tag == 'w':
            # Get the values of <w> element properties
            self.id = self.node.get('id')
            self.map['t'] = self.node.get('t')
            self.map['lang'] = self.node.get('l')
            # Original word
            self.map['o'] = {}
            or_el = self.node.find('o')
            self.map['o']['text'] = or_el.text
            self.map['o']['tail'] = ''
            # If has break (line, page or column) get the tail
            bk = or_el.find('bk')
            if bk is not None:
                self.map['o']['tail'] += (bk.tail or '')
            self.map['o']['fon'] = or_el.get('fon') or ''
            if self.node.get('l'):
                self.lang = self.node.get('l')
            # Process comments elements
            for comm in self.node.findall('comment'):
                c_obj = Comment(self, comm)
                self.comments_list.append(c_obj)
            # Phonological string
            fon_el = self.node.find('f')
            if fon_el is not None:
                if fon_el.text is None or fon_el.text.strip() == '':
                    # Remove empty <f> element from the tree
                    self.node.remove(fon_el)
                else:
                    self.map['f'] = {}
                    self.map['f']['text'] = fon_el.text
            # Format
            if self.node.get('f') is not None:
                self.setFormat(self.node.get('f').split(','), False)
            self.capitular = (self.node.get('cap') is not None and self.node.get('cap') == 'true')
            # Handle editions (if any)
            self._on_ed()
        # Incorrect XML: text inside <w> but outside <o>|<e>
        if 'edition' in self.map and self.text is not None:
            __builtin__.log(_(u"Aviso: palavra com mais de um nó contendo texto; usando versão editada.")+'\n')

    def _get_ed_mark_text(self, tag, em, text=''):
        for i in em.getchildren():
            if i.tag == tag:
                text += i.text or '' + ' '
                for j in i.getchildren():
                    if j.tag == 'ed_mark':
                        text += self._get_ed_mark_text(j, text)
                    text += j.tail or '' + ' '
                text += i.tail or '' + ' '
        text += em.tail or '' + ' '
        return text

    def _on_ed(self):
        '''Handle edition nodes for a <w> element (2008 style)'''
        # Search immediate <e> child nodes (prevent erros bellow*)
        if self.node.find('e') is None:
            return
        if not self.isEdited():
            self.map['edition'] = {}
        has_seg = False
        for n in self.node.findall('e'):
            if n.get('t') == 'seg':
                has_seg = True
                break
        # Iterate over the <e> nodes (*even [undesired] not immediate ones)
        for n in self.node.findall('e'):
            if n.get('t') == 'jun':
                self.has_merge = True
            if n.text.find(' ') > 0 and not has_seg:
                # Ensure that segmentations are marked 'seg'
                n.set('t','seg')
                has_seg = True
            if n.get('t') == 'seg':
                self.setMorfStrings(n.text.split(' '))
            self.map['edition'][n.get('t')] = {}
            try:
                self.map['edition'][n.get('t')]['text'] = n.text or ''
            except:
                #TODO:talvez, eliminar o elemento 'e' vazio.
                pass

    def __str__(self):
        return self.getString()
    
    def isEdited(self, ed_type=''):
        """
        Return {True} if this is an edited word; {False} otherwise.
        """
        if 'edition' in self.map:
            return (ed_type == '' or ed_type in self.map['edition']) 
        return False
    
    def getId(self):
        return self.id
    
    def getEditedString(self, ed_type):
        """
        Returns the string of the edited version of the word, or {None} if word
        is not an edited word.
        """
        if self.isEdited() and ed_type in self.map['edition']:
            return self.map['edition'][ed_type]['text']
        return ''

    def getOriginalString(self, sep=''):
        """
        Returns the string of the original version of the word, or {None} if word
        is not an edited word. (2008 style)
        """
        text = self.map['o']['text']
        if self.node.find('o').find('bk') is not None:
            text += sep + self.map['o']['tail']
        return text

    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        text = u''

        # Some types of words are not relevant for linguistic analyses
        if 'w:'+self.getType() not in ignore_list:
            # Get correct edition level for the word
            word_str = self.getOriginalString('|')
            if self.isEdited():
                # The selected level is the "maximum" one: so search for it or for its forerunners
                for ed in ed_level:
                    ed_str = self.getEditedString(ed)
                    if len(ed_str) > 0:
                        word_str = ed_str.replace('_',' ')
                        break
                
            if 'PRINT_EL_TYPE' in options and self.getType() != '':
                text = u'['+self.getType()+': ' + word_str + ']'
            else:
                text = ''
                if 'PHONOLOGICAL_TEXT' in options:
                    text = self.getPhonologicalString()
                if len(text) == 0:
                    # Not 'phonology' or there is no phonological form defined
                    text = word_str
    
        # Line breaks
        if self.getBreakType() != '':
            if 'DO_BREAKLINES' in options and self.getBreakType() == 'l':
                if text.find('|') >= 0:
                    text = text.replace('|','\n')
                else:
                    text += '\n'
            else:
                text = text.replace('|',' ')
                # Page number
                if 'TOOLS_TEXT_ONLY' not in options and self.getBreakType() == 'p':
                    text += '\n\n[page: ' + str(self.containing_page) + ']\n\n'

        return text

    def exportToHtml(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        text = u''

        # Some types of words are not relevant for linguistic analyses
        if 'w:'+self.getType() not in ignore_list:
            # Get correct edition level for the word
            if len(ed_level) == 1:
                word_str = self.getOriginalString('|')
                alt_str = self.getString().replace('_',' ')
            else:
                # Apenas edições até o nível especificado
                word_str = self.getString(ed_level).replace('_',' ')
                alt_str = self.getOriginalString('|')
                
            alt_str = alt_str.replace('|',' ')

            text = ''
            if 'PHONOLOGICAL_TEXT' in options:
                text = cgi.escape(self.getPhonologicalString()).strip()
            if len(text) == 0:
                # Not 'phonology' or there is no phonological form defined
                text = cgi.escape(word_str).strip()
                
            if self.isCapitular():
                aux = ''
                if len(text) > 1:
                    aux += text[1:]
                text = '<div class="cap">' + text[0] + '</div>' + aux

            f_type = ''
            if self.getType() != '':
                f_type = 'class="' + self.getType() + '"'
                if 'PRINT_EL_TYPE' in options:
                    text = u'<span class="el_type_color">[</span><span class="el_type">'+self.getType()+'</span> ' + text + '<span class="el_type_color">]</span>'

            # Line breaks
            if self.getBreakType() != '':
                if 'DO_BREAKLINES' in options and self.getBreakType() == 'l':
                    if text.find('|') >= 0:
                        text = text.replace('|','<br/>')
                    else:
                        text += '<br/>'
                else:
                    text = text.replace('|',' ')
                    # Page number
                    if self.getBreakType() == 'p':
                        text += '<br/><br/>[page: ' + str(self.containing_page) + ']<br/><br/>'

            # Hover text for alternate version
            if word_str.replace('|',' ').strip() != alt_str.strip():
                text = '<a href="#' + self.getId() + '" title="' + alt_str + '" name="' + alt_str +'">' + text + '</a>'
    
            # Format
            f_aux = ''
            if self.isBold(): f_aux += 'font-weight:bold;'
            if self.isItalic(): f_aux = 'font-style:italic;'
            if self.isUnderlined(): f_aux = 'text-decoration:underline;'
            
            if len(f_type+f_aux) > 0:
                text = '<word ' + f_type + ' style="' + f_aux + '">' + text + '</word>'
        else:
            # Line breaks
            if self.getBreakType() != '':
                if 'DO_BREAKLINES' in options and self.getBreakType() == 'l':
                    if text.find('|') >= 0:
                        text = text.replace('|','<br/>')
                    else:
                        text += '<br/>'
                else:
                    text = text.replace('|',' ')
                    # Page number
                    if self.getBreakType() == 'p':
                        text += '<br/><br/>[page: ' + str(self.containing_page) + ']<br/><br/>'

        return text

    def getString(self, ed_types=[]):
        """
        Returns the word's string. If word is edited, returns the new version
        following the order of priority defined in Preferences.

        (to retrieve the original version use {getOriginalString()})
        """
        if self.isEdited():
            #ed_types = []
            if len(ed_types) == 0 and __builtin__.cfg.get(u'Preferences', u'EditionTypes') != '':
                for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                    type, label = ed.split('|')
                    ed_types.append(type)
                ed_types.reverse()
            # Return the first found edition type by the order defined bellow
            for ed_type in ed_types:
                if ed_type in self.map['edition']:
                    return self.getEditedString(ed_type).replace(' ','_')
        return self.getOriginalString().replace(' ','_')
    
    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        if page_nr != self.containing_page:
            return u''
        head = u'<word id="%s">'%self.loc
        foot = u'</word>'
        if True: #self.focus:
            head += '<a name="%s">'%self.loc
            foot = '</a>' + foot
        if self.isEdited():
            head += '<font color="red">'
            foot = '</font>' + foot
        else:
            head += '<font color="black">'
            foot = '</font>' + foot
        if self.bold:
            head += '<b>'
            foot = '</b>' + foot
        if self.italic:
            head += '<i>'
            foot = '</i>' + foot
        if self.underline:
            head += '<u>'
            foot = '</u>' + foot
        text = u''
        b = self.node.find('o').find('bk')
        if b is not None:
            if b.get('t') == 'l':
                if not eval(__builtin__.cfg.get(u'Preferences', u'Line_break')):
                    text = ' <font color="gray">\</font> '
                else:
                    text = ' <font color="gray">\</font><br>'
            if b.get('t') == 'c':
                text = ' <font color="gray">\\\</font> '
        if self.node.get('t') is not None:
            pass
        if len(self.comments_list) > 0:
            foot += '<sub><font color="green" size="-2">+</font></sub>'  
        return head + cgi.escape(self.getString(ed_level)) + foot + text

    def getHtmlPOSVersion(self, page_nr, ed_level=[], sep='/'):
        '''
        Get the HTML POS version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        if page_nr != self.containing_page or self.getString().replace("_",'').strip() == "":
            return u''
        rt = u''
        ii = 0
        word_seg = self.getString(ed_level).split('_')
        for seg in word_seg:
            head = u'<word id="%s:%s">'%(self.loc, ii)
            foot = u'</word>'
            if True: #self.focus:
                head += u'<a id="%s:%s">'%(self.loc, ii)
                foot = '</a>' + foot
            if self.isRelevantToPOS():
                if self.isEdited():
                    head += '<font color="red">'
                    foot = '</font>' + foot
                else:
                    head += '<font color="black">'
                    foot = '</font>' + foot
            else:
                head += '<font color="gray">'
                foot = '</font>' + foot
                
            if self.pos_modified:
                head += '<b>'
                foot = '</b>' + foot

            if self.node.get('t') is not None:
                pass

            pos_info = ''
            if self.isRelevantToPOS():
                try:
                    pos_info = sep + self.getPrettyPartOfSpeech()[ii]
                except:
                    pass

            rt += head + seg + pos_info + foot + ' '
            ii += 1
        return rt

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        ignore_list = []
        if __builtin__.cfg.get(u'Preferences', u'ElementTypes') != '':
            for p in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                while p.count('|') <= 2:
                    p += '|'
                el, desc, pos, css = p.split('|')
                if el == _(u'Palavra') and pos == _(u'ignorar'):
                    ignore_list.append(desc)
        return (self.getType() not in ignore_list and self.parent.isRelevantToPOS()) 
        
    def isOriginalAsFon(self):
        """
        Check whether the original word has 'fon=true' 
        """
        or_el = self.node.find('o')
        if (or_el.get('fon') and or_el.get('fon') == 'true'):
            return True
        return False

    def setOriginalAsFon(self, fon):
        """
        Set the original word 'fon' property
        """
        or_el = self.node.find('o')
        if fon:
            or_el.set('fon', 'true')
            self.map['o']['fon'] = 'true'

    def setOriginalString(self, text, bk_node = None):
        """
        Set the original text (in case of wrong transcriptions)
        bk_node --> Used on 'junction' operations
        """
        or_el = self.node.find('o')
        or_el.text = text.split('|')[0]
        self.map['o']['text'] = text.split('|')[0]
        if bk_node is not None: # There is a break in the next word (junction)
            or_el.append(bk_node)
        bk_el = or_el.find('bk')
        if bk_el is not None:
            if text.find('|') < 0:
                # The 'break mark' cannot be excluded manually in the original form
                text += '|'
            if len(text.split("|")) == 2:
                bk_el.tail = text.split("|")[1]
                self.map['o']['tail'] = text.split('|')[1]
        elif text.find('|') >= 0:
            # The 'break mark' cannot be included manually in the original form
            text = text.replace('|','')

    def getPhonologicalString(self):
        """
        Get the specific fonological form
        """
        fon_el = self.node.find('f')
        if fon_el is not None:
            if fon_el.text is None or fon_el.text.strip() == '':
                # Remove empty <f> element from the tree
                self.node.remove(fon_el)
                del self.map['f']
                return ''
            return fon_el.text
        return ''

    def setPhonologicalString(self, text):
        """
        Set a specific fonological form
        """
        fon_el = self.node.find('f')
        if fon_el is not None:
            if text.strip() == '':
                # Remove empty <f> element from the tree
                self.node.remove(fon_el)
                del self.map['f']
                return
            else:
                fon_el.text = text
        else:
            if len(text.strip()) == 0:
                return
            fon_el = etree.SubElement(self.node, 'f') #, id=self.id+'#fon')
            fon_el.text = text
            self.map['f'] = {}
        self.map['f']['text'] = text

    def setEdition(self, ed_text, ed_type, text_obj=None, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Insert or update an edition.
        '''
        undo_tmp = []
        # Try to update an existing edition (if any)
        if self.isEdited():
            for ed_el in self.node.findall('e'):
                if ed_el.get('t') == ed_type: 
                    if ed_type == 'jun' and\
                            not ed_text == ''.join(self.getOriginalString().split()):
                        rt, msg = text_obj.mergeToNextWord(self, undo_tmp, undo_text, undo_pg)
                        if not rt:
                            return False, msg
                    ed_el.text = ed_text
                    self.map['edition'][ed_type]['text'] = ed_text
                    if ed_type == 'seg':
                        self.setMorfStrings(ed_text.split(' '))
                    return True, ''

        # Merge this node with the next one, if ed_type is 'jun'
        if ed_type == 'jun' and \
                not ed_text == ''.join(self.getOriginalString().split()):
            rt, msg = text_obj.mergeToNextWord(self, undo_tmp, undo_text, undo_pg)
            if not rt:
                return False, msg
            self.has_merge = True

        if not self.isEdited():
            self.map['edition'] = {}

        # If it gets here, it is a new edition 
        new_ed = etree.SubElement(self.node, 'e', t=ed_type)
        new_ed.text = ed_text
        # Create the dictionary for the edition
        self.map['edition'][ed_type] = {}
        self.map['edition'][ed_type]['text'] = ed_text

        if undo_stack is not None and len(undo_tmp) > 0:
            # In case of 'junction'
            undo_stack[0][2].append(undo_tmp[0])

        return True, '' 
        
    def clearEditions(self, ed_list=[], text_obj=None, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Remove the specified editions. If no edition type is given
        or 'jun' is in the list then remove all.
        '''
        if self.isEdited():
            if 'jun' in ed_list:
                ed_list = [] # Once 'jun' is removed, E-Dictor removes all editions
            for ed in self.node.findall('e'):
                if len(ed_list) == 0 or (ed.get('t') in ed_list):
                    self.node.remove(ed)
                    try:
                        del self.map['edition'][ed.get('t')]
                    except: pass
            if len(self.map['edition']) == 0:
                del self.map['edition']
            if len(ed_list) == 0 and self.has_merge \
                    and text_obj.unmergeToNextWord(self, undo_stack, undo_text, undo_pg):
                self.has_merge = False

    def setMorfStrings(self, wlist):
        '''
        Update or include new <m> itens to store the 
        parts of the segmented word (two or more).
        ''' 
        if len(wlist) == 1:
            return
        ii = 0
        for w in wlist:
            morf_el = self.node.findall('m')
            if len(morf_el) > ii:
                morf_el[ii].text = w
            else:
                morf_el = etree.SubElement(self.node, 'm') #, id=self.id+'#m'+str(ii))
                morf_el.text = w
            ii += 1

    def hasPartOfSpeech(self):
        ''' Check whether this word has POS tags '''
        pos_tags = self.getPartOfSpeech()
        if len(pos_tags) == 0 or (len(pos_tags) == 1 and pos_tags[0] == u''): 
            return False
        else:
            return True
        
    def getPrettyPartOfSpeech(self):
        morf_el = self.node.find('m')
        if morf_el is None:
            return [u'']
        else:
            morf_list = []
            morf_els = self.node.findall('m')
            for morf_el in morf_els:
                morf_list.append(u'' + (morf_el.get('v') or ''))
            return morf_list
        
    def getPartOfSpeech(self):
        morf_el = self.node.find('m')
        if morf_el is None:
            return [u'']
        else:
            morf_list = []
            morf_els = self.node.findall('m')
            for morf_el in morf_els:
                morf_list.append((morf_el.get('v') or u''))
            return morf_list

    def setPartOfSpeech(self, pos_tag, ii):
        morf_list = []
        morf_els = self.node.findall('m')
        for morf_el in morf_els:
            morf_list.append(morf_el)
        while len(morf_list) <= ii:
            morf_el = etree.SubElement(self.node, 'm')
            morf_list.append(morf_el)
        morf_list[ii].set('v', pos_tag)
        self.pos_modified = True

    def getType(self):
        return self.map['t'] or ''
    
    def setType(self, type):
        self.node.set('t', type)
        self.map['t'] = type

    def getComments(self):
        comm_list = []
        for comm in self.comments_list:
            c = {}
            c['author'] = comm.getAuthor()
            c['date']   = comm.getDate()
            c['title']  = comm.getTitle()
            c['text']   = comm.getText()
            c['remove'] = False
            comm_list.append(c)
        return comm_list

    def setComments(self, comm_list):
        '''
        Set the comment elements for the object and its node.
        '''
        ii = 0
        for comm in comm_list:
            if not comm['remove']: 
                if ii >= len(self.comments_list):
                    comm_node = etree.SubElement(self.node, 'comment')
                    self.comments_list.append(Comment(self, comm_node))
                
                self.comments_list[ii].setAuthor(comm['author'])
                self.comments_list[ii].setDate(comm['date'])
                self.comments_list[ii].setTitle(comm['title'])
                self.comments_list[ii].setText(comm['text'])
            ii += 1

        ii = 0
        for comm in comm_list:
            if comm['remove']: 
                self.node.remove(self.comments_list[ii].node)
                del self.comments_list[ii]
            ii += 1
    
    def getLanguage(self):
        return self.map['lang'] or ''
    
    def setLanguage(self, lang):
        if lang != '':
            self.node.set('l', lang)
        elif 'l' in self.node.attrib:
            del self.node.attrib['l']
        self.map['lang'] = lang

    def setFocused(self, f):
        self.focus = f
        
    def setFormat(self, format, set_node=True):
        self.bold = ('b' in format or self.parent.isBold())
        self.italic = ('i' in format or self.parent.isItalic())
        self.underline = ('u' in format or self.parent.isUnderlined())
        if set_node:
            self.node.set('f', ','.join(format))
    
    def isBold(self):
        return (self.node.get('f') is not None and 'b' in self.node.get('f').split(','))
    
    def isItalic(self):
        return (self.node.get('f') is not None and 'i' in self.node.get('f').split(','))
    
    def isUnderlined(self):
        return (self.node.get('f') is not None and 'u' in self.node.get('f').split(','))

    def isCapitular(self):
        return self.capitular
    
    def setCapitular(self, cap):
        self.capitular = cap
        if cap:
            self.node.set('cap','true')
        elif self.node.get('cap'):
            del self.node.attrib['cap']
            
    def getParent(self):
        return self.parent

    def setParent(self, parent):
        self.parent = parent

    def setNode(self, node):
        self.node = node
    
    def setPage(self, page_nr):
        self.containing_page = page_nr
        self.parent.setPage(page_nr)

    def insertBreak(self, or_string, type, options=[], line_nr='n/i', undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Insert a <bk> element in the <o> element of the word.
        Optionally, add header/footer and line_nr elements.
        '''
        # Procede with the operation
        or_el = self.node.find('o')
            
        # Set the information needed to undo the operation
        if undo_stack is not None:
            undo_stack.insert(0,['BREAK', self, self.node.__deepcopy__(False), self.parent.elements_list.index(self),
                                 self.node.getparent().index(self.node), undo_text, undo_pg, _(u'Desfazer quebra.')])
        if or_el.find('bk') is not None:
            self.removeBreak(None)
        break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t=type)
        __builtin__.ids['bk'] += 1
        if len(options) > 0:
            if 'ln' in options:
                text_el = etree.SubElement(break_el, 'te', id='te_'+str(__builtin__.ids['te']), t='ln')
                __builtin__.ids['te'] += 1
                w_el = etree.SubElement(text_el, 'w', id=str(__builtin__.ids['w'])) #text_el.get('id')+'#0')
                __builtin__.ids['w'] += 1
                te_or_el = etree.SubElement(w_el, 'o') #, id=w_el.get('id')+'#o')
                te_or_el.text = line_nr
        self.setOriginalString(or_string)
        
    def removeBreak(self, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Remove the break element from inside the word. ATTENTION:
        pages list must be updated after this method execution!
        '''
        if self.getOriginalString('|').find('|') < 0:
            return False
        try:
            or_el = self.node.find('o')
            bk_el = or_el.find('bk')
            # Set the information needed to undo the operation
            if undo_stack is not None:
                undo_stack.insert(0,['REMOVE_BK', self, self.node.__deepcopy__(False),
                                     self.parent.elements_list.index(self),
                                     self.node.getparent().index(self.node), undo_text, undo_pg,
                                     _(u'Desfazer remoção de quebra.')])
            or_el.text += (bk_el.tail or '')
            self.map['o']['text'] = or_el.text
            self.map['o']['tail'] = ''
            or_el.remove(bk_el)
            return True
        except:
            raise
        return False

    def getBreakType(self):
        '''
        Returns the type of break element (if any).
        '''
        try:
            bk_el = self.node.find('o').find('bk')
            return bk_el.get('t')
        except:
            pass
        return ''

    def hasBreak(self, type=None):
        ''' Returns true or false '''
        return ((type is None and self.node.find('o').find('bk') is not None) or\
                (self.node.find('o').find('bk') is not None and self.node.find('o').find('bk').get('t') == type)) 

    
class Sentence():
    '''
    This class wraps the subtrees of the document, included between
    <s></s> and provides specific operations over its content.
    '''
    def __init__(self, parent, node):
        self.id = node.attrib.get('id')
        self.num = -1
        self.node = node
        self.parent = parent
        self.pages = []
        self.elements_list = []
        self.type = ''
        if self.node.get('t') is not None:
            self.type = self.node.get('t')
        self.lang = '' 
        if self.node.get('l') is not None:
            self.lang = self.node.get('l') 
        # Process word nodes
        self._build()
        # Apply the format defined to the subelements
        if node.get('f'):
            self.setFormat(node.get('f'))
            
    def setFormat(self, format):
        '''
        Apply the format defined to the sentence to all of its
        words.
        '''
        for el in self.getWordsList():
            if isinstance(el, (Word)):
                el.setFormat(format, False)

    def isBold(self):
        return (self.node.get('f') is not None and 'b' in self.node.get('f').split(',')) or self.parent.isBold()
    
    def isItalic(self):
        return (self.node.get('f') is not None and 'i' in self.node.get('f').split(',')) or self.parent.isItalic()
    
    def isUnderlined(self):
        return (self.node.get('f') is not None and 'u' in self.node.get('f').split(',')) or self.parent.isUnderlined()

    def getParent(self):
        return self.parent
        
    def __str__(self):
        return self.getString().encode('utf-8')
    
    def _build(self):
        if self.node.tag != 's':
            raise XMLValidationError, (_(u"Elemento '%s' inválido para construção de sentença.")%self.node.tag).encode('utf-8')
        # First: split text inside <s> and create a <w> element for each word and each different node (like 'ed_mark').
        word_els = self._build_get_word_nodes(self.node.text, 0)
        self.node.text = None
        if word_els is not None:
            if len(word_els) > 0:
                self.node.insert(0, word_els[0])
            for i in range(1, len(word_els)):
                self.node.insert(i, word_els[i])
            del word_els[:]
        iword = 0
        inode = 0
        for c in self.node.getchildren():
            if c.find('o').text is None or c.find('o').text == '':
                self.node.remove(c)
                continue
            if c.tag == 'ed_mark':   # semicodified files (2007 style)
                loc = str(__builtin__.ids['w']) #self.id + '#' + str(iword)
                __builtin__.ids['w'] += 1
                new_el = self.node.makeelement('w', id=loc)
                new_el.append(c)
                self.node.insert(inode, new_el)
                self.elements_list.insert(iword, Word(self, new_el, new_el.attrib.get('id')))
                iword += 1
                inode += 1
                if c.tail:
                    tmp_els = self._build_get_word_nodes(c.tail, iword)
                    if tmp_els is not None:
                        for ne in tmp_els:
                            self.node.insert(inode, ne)
                            self.elements_list.insert(iword, Word(self, ne, ne.attrib.get('id')))
                            iword += 1
                            inode += 1
                    c.tail = None
            elif c.tag == 'w':   # semicodified files
                self.elements_list.insert(iword, Word(self, c, c.attrib.get('id')))
                iword += 1
                inode += 1
            else:
                inode += 1
                if c.tail:
                    tmp_els = self._build_get_word_nodes(c.tail, iword)
                    if tmp_els:
                        for ne in tmp_els:
                            self.node.insert(inode, ne)
                            self.elements_list.insert(iword, Word(self, ne, ne.attrib.get('id')))
                            iword += 1
                            inode += 1
                    c.tail = None
        

    def _build_get_word_nodes(self, text, i=0):
        words = []
        if text is not None and text.strip() is not None:
            # Trying a more "inteligent" (a bit dangerous) tokenization...
            new_el = None
            or_el = None
            for tk in contrib_nltk.tokenize.regexp(text, r'[^\s]+'):
                for t in contrib_nltk.tokenize.regexp(tk, r'@[0-9]+@|@pag@|@ln@|@col@|(\w+)?\$*(([\.,])?\d+)(([\.,])?\d+)?(([\.,])?\d+)?\$*|([\'~])?[\w\d]+([$\'~-])?([\w\d]+)?|(\.\.)?[^\w]'):
                    if len(t) <= 2 or (t[0] != '@' and t[-1] != '@'):
                        loc = str(__builtin__.ids['w']) #self.id + '#' + str(i)
                        __builtin__.ids['w'] += 1
                        new_el = self.node.makeelement('w', id=loc)
                        or_el  = etree.SubElement(new_el, 'o') #, id=loc+'#o')
                        or_el.text = t.strip()
                        words.append(new_el)
                        i += 1
                    elif new_el is not None and len(t) > 1 and t[0] == '@' and t[-1] == '@':
                        if t == "@pag@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='p')
                                __builtin__.ids['bk'] += 1
                        elif t == "@ln@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='l')
                                __builtin__.ids['bk'] += 1
                        elif t == "@col@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='c')
                                __builtin__.ids['bk'] += 1
                        else:
                            (ab,author,date,title,txt,fc) = self.node.get('comm'+t.replace('@','')).split(':')
                            comm_node = etree.SubElement(new_el, 'comment')
                            comm_obj = Comment(self, comm_node)
                            comm_obj.setAuthor(author)
                            comm_obj.setDate(date)
                            comm_obj.setTitle(title)
                            comm_obj.setText(txt)
                            self.node.set('comm'+t.replace('@',''),'')
            return words
        else:
            return None

    def getId(self):
        return self.id
    
    def getWordByNum(self, num):
        if num < len(self.elements_list):
            return self.elements_list[num]
        return None
    
    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        # Some types of words are not relevant for linguistic analyses
        if 's:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '\n\n[page: ' + str(w_obj.containing_page) + ']\n\n'
            return text
        
        before = u''
        after = u''
        if 'PRINT_EL_TYPE' in options and len(self.getType()) > 0:
            before = u'[' + self.getType() + ': '
            after = ']'
        if 'TOOLS_TEXT_ONLY' not in options and 'LINEBREAK_ON_SENTENCE' in options:
            before += u'[' + self.node.get('id') + '] '

        text = self.elements_list[0].exportToText(ed_level, options, ignore_list)
        for w in self.elements_list[1:]:
            text += ' ' + w.exportToText(ed_level, options, ignore_list)

        # Adapt the sentence string stripping spaces before punctuation
        text = re.sub(r' +([^\w])', r'\1', text, re.IGNORECASE | re.UNICODE)
        text = re.sub(r'([({\[]) +', r'\1', text)
        text = re.sub(r'([^ "])"(\w)', r'\1 "\2', text, re.IGNORECASE | re.UNICODE)
        text = re.sub(r' +', r' ', text)
        
        text = u' ' + before + text + after
        
        # Fix the [page] position
        text = re.sub(r' *(\n\n\[page[^\]]+\]\n\n)\]', r']\1', text)
        
        if 'LINEBREAK_ON_SENTENCE' in options:
            text += '\n\n'
            
        return text

    def exportToHtml(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        if len(self.elements_list) == 0:
            return ''
         
        # Some types of words are not relevant for linguistic analyses
        if 's:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '<br/><br/>[page: ' + str(w_obj.containing_page) + ']<br/><br/>'
            return text
        
        before = u''
        after = u''
        f_type = u''
        if len(self.getType()) > 0:
            f_type = 'class="' + self.getType() + '"'
            if 'PRINT_EL_TYPE' in options:
                before = u'<span class="el_type_color">[</span><span class="el_type">' + self.getType() + '</span> '
                after = '<span class="el_type_color">]</span>'

        if 'TOOLS_TEXT_ONLY' not in options and 'LINEBREAK_ON_SENTENCE' in options:
            before += u'[' + self.node.get('id') + '] '

        text = self.elements_list[0].exportToHtml(ed_level, options, ignore_list)
        quote = 0
        punct_list = ['.',',',':',';','?','!','"']
        for w in self.elements_list[1:]:
            # Adapt the sentence string stripping spaces before punctuations
            w_str = w.getString()
            if w_str[0] not in punct_list or (re.search(r'[\w]', w_str, re.IGNORECASE | re.UNICODE) is not None and quote == 0):
                text += ' '
            if w.getString() == '"': # Works only for stardard quote character
                if quote == 0:
                    text += ' '
                    quote = 1
                else:
                    quote = 0
            elif quote == 1:
                quote = 0
            text += w.exportToHtml(ed_level, options, ignore_list)

        # Format
        f_aux = ''
        if self.isBold(): f_aux += 'font-weight:bold;'
        if self.isItalic(): f_aux = 'font-style:italic;'
        if self.isUnderlined(): f_aux = 'text-decoration:underline;'
        
        text = '<span ' + f_type + ' style="' + f_aux + '">' + text + '</span>'
        
        text = u' ' + before + text + after

        # Fix the [page] position
        text = re.sub(r' *(<br/><br/>\[page[^\]]+\]<br/><br/></span>)<span class="el_type_color">\]</span>', r'<span class="el_type_color">]</span>\1', text)

        if 'LINEBREAK_ON_SENTENCE' in options:
            text += '<br/>'
            
        return text

    def getString(self):
        '''
        Returns the content of this object in a string format.
        '''
        text = u''
        for w in self.elements_list:
            text += w.getString() + ' '
        return text
    
    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        text = u''
        if page_nr in self.pages:
            for w_obj in self.getWordsList():
                text += w_obj.getHtmlVersion(page_nr, ed_level) + ' '
            if self.getWordsList()[0].getHtmlVersion(page_nr, ed_level) == '':
                # There are words of this sentence in the previous page
                text = '<font size="1" color="gray">[...]</font> ' + text
            if self.getWordsList()[len(self.getWordsList())-1].getHtmlVersion(page_nr, ed_level) == '':
                # There are words of this sentence in the next page
                text += ' <font size="1" color="gray">[...]</font>'
        if len(text.strip()) > 0:
            lang = ''
            type = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = ':'+self.type
            text = u'<word id=' + self.getId() +\
                    '><font size="1" color="gray">[s'+type+lang+']</font></word> ' +\
                    text
        return text
    
    def getHtmlPOSVersion(self, page_nr, ed_level):
        '''
        Get the HTML POS version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        text = u''
        lang = ''
        type = ''
        if self.lang != '':
            lang = ':'+self.lang
        if self.type != '':
            type = ':'+self.type
        if page_nr in self.pages:
            for w_obj in self.getWordsList():
                text += w_obj.getHtmlPOSVersion(page_nr, ed_level, '/') + ' '
            if self.getWordsList()[0].getHtmlVersion(page_nr, ed_level) == '':
                # There are words of this sentence in the previous page
                text = '<font size="1" color="gray">[...]</font> ' + text
            if self.getWordsList()[len(self.getWordsList())-1].getHtmlVersion(page_nr, ed_level) == '':
                # There are words of this sentence in the next page
                text += ' <font size="1" color="gray">[...]</font>'
        if len(text.strip()) > 0:
            text = u'<word id=' + self.getId() +\
                    '><font size="1" color="gray">[s'+type+lang+']</font></word> ' +\
                    text
        return text

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        ignore_list = []
        if __builtin__.cfg.get(u'Preferences', u'ElementTypes') != '':
            for p in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                while p.count('|') <= 2:
                    p += '|'
                el, desc, pos, css = p.split('|')
                if el == _(u'Sentença') and pos == _(u'ignorar'):
                    ignore_list.append(desc)
        return (self.getType() not in ignore_list and self.getLanguage() == '' and self.parent.isRelevantToPOS()) 
        
    def exportToWordTagFormat(self, ed_level=['seg'], options=[], POS=True):
        text = u''
        if self.isRelevantToPOS():
            for wordObj in self.elements_list:
                if len(ed_level) == 0:
                    # Used when exporting text only (no tags)
                    w_str = wordObj.getString().replace("/",'-')
                else:
                    w_str = wordObj.getString(ed_level).replace("/",'-')
#                    w_str = wordObj.getOriginalString().replace("/",'-')
#                    for ed in ed_level:
#                        if wordObj.isEdited(ed):
#                            w_str = wordObj.getEditedString(ed).replace("/",'-')
#                            break
                if w_str.replace("_","").strip() == '':
                    continue
                if wordObj.isRelevantToPOS():
                    w_list = w_str.split('_')
                    pos_list = []
                    if wordObj.hasPartOfSpeech():
                        pos_list = wordObj.getPartOfSpeech()
                    for ii in range(len(w_list)):
                        text += w_list[ii]    
                        if POS and len(pos_list) > ii and pos_list[ii].strip() != '':
                            text +=  '/' + pos_list[ii]
                        text += ' '
            text.rstrip()

            if 'IDs' in options:
                text += '{XML},'+str(self.pages[0])+'.'+self.id.replace('s_','')+'/ID'
                
            # Inverte o número de página com o ID, se necessário (evita: <P_9>/CODE nome/ID)
            #text = re.sub(r'(<P_[^ ]*?) ([^ ]*?/ID)', r'\2\n\n\1', text)

        if 'PAGES' in options:
            for wordObj in self.elements_list:
                if wordObj.hasBreak('p'):
                    text += '\n\n<P_' + str(wordObj.containing_page+1) + '>/CODE'
            
        return text + '\n\n'
    
    def getType(self):
        return self.type
    
    def setType(self, type):
        if type.strip() != '':
            self.node.set('t', type)
        elif 't' in self.node.attrib:
            del self.node.attrib['t']
        self.type = type

    def getLanguage(self):
        return self.lang
    
    def setLanguage(self, lang):
        if lang != '':
            self.node.set('l', lang)
        elif 'l' in self.node.attrib:
            del self.node.attrib['l']
        self.lang = lang
        
    def getWordsList(self):
        return self.elements_list[:]

    def removeWord(self, word):
        '''
        Remove a word object from the sentence list of words.
        '''
        if word in self.elements_list:
            self.elements_list.remove(word)
            self.node.remove(word.node)
        # If the sentence has no more words, remove it
        if len(self.getWordsList()) == 0:
            self.parent.remove(self)
        self.adjustPages()
    
    def rebuild(self, node):
        '''
        Rebuild the Sentence object based on the node specified.
        '''
        self.__init__(self.parent, node)
        
    def setPage(self, page_nr):
        if page_nr not in self.pages:
            self.pages.append(page_nr)
            self.parent.setPage(page_nr)

    def adjustPages(self):
        self.pages = []
        for w_obj in self.elements_list:
            self.setPage(w_obj.containing_page)

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]

   
class Paragraph():
    '''
    This class wraps the subtrees of the document, included between
    <p></p> and provides specific operations over its content.
    '''
    def __init__(self, parent, node):
        self.node = node
        self.parent = parent
        self.elements_list = []
        self.comments_list = []
        self.pages = []
        self.type = ''
        if self.node.get('t') is not None:
            self.type = self.node.get('t')
        self.lang = ''
        if self.node.get('l') is not None:
            self.lang = self.node.get('l')
        # Process child elements 
        for el in node.getchildren():
            el_obj = None
            if el.tag == 's':
                el_obj = Sentence(self, el)
            elif el.tag == 'te' and el.get('t') == 'pn':
                el_obj = TextElement(self, el)
            elif el.tag != 'comment':
                __builtin__.log(_(u"XML mal formado") + " (Paragraph.__init__, id=" + str(el.get('id')) + ' ' +\
                                str(el) + ' ' + str(el.attrib) + ")\n")
            if el_obj is not None:
                self.elements_list.append(el_obj)
        # Process comments elements
        for comm in node.findall('comment'):
            c_obj = Comment(self, comm)
            self.comments_list.append(c_obj)
        # Apply the format defined to the subelements
        if node.get('f'):
            self.setFormat(node.get('f'))

    def getId(self):
        return self.node.get('id')

    def remove(self, el):
        '''
        Removes an element from the list.
        '''
        if el in self.elements_list:
            self.elements_list.remove(el)
            self.node.remove(el.node)
        if len(self.getWordsList()) == 0:
            self.parent.remove(self)
        self.adjustPages()

    def setFormat(self, format):
        '''
        Apply the format defined in the paragraph to all of its
        sentences.
        '''
        for el in self.elements_list:
            if isinstance(el, (Sentence)):
                el.setFormat(format)

    def isBold(self):
        return (self.node.get('f') is not None and 'b' in self.node.get('f').split(',')) or self.parent.isBold()
    
    def isItalic(self):
        return (self.node.get('f') is not None and 'i' in self.node.get('f').split(',')) or self.parent.isItalic()
    
    def isUnderlined(self):
        return (self.node.get('f') is not None and 'u' in self.node.get('f').split(',')) or self.parent.isUnderlined()

    def getType(self):
        return self.type
    
    def setType(self, type):
        if type.strip() != '':
            self.node.set('t', type)
        elif 't' in self.node.attrib:
            del self.node.attrib['t']
        self.type = type

    def getComments(self):
        comm_list = []
        for comm in self.comments_list:
            c = {}
            c['author'] = comm.getAuthor()
            c['date']   = comm.getDate()
            c['title']  = comm.getTitle()
            c['text']   = comm.getText()
            c['remove'] = False
            comm_list.append(c)
        return comm_list

    def setComments(self, comm_list):
        '''
        Set the comment elements for the object and its node.
        '''
        ii = 0
        for comm in comm_list:
            if not comm['remove']: 
                if ii >= len(self.comments_list):
                    comm_node = etree.SubElement(self.node, 'comment')
                    self.comments_list.append(Comment(self, comm_node))
                
                self.comments_list[ii].setAuthor(comm['author'])
                self.comments_list[ii].setDate(comm['date'])
                self.comments_list[ii].setTitle(comm['title'])
                self.comments_list[ii].setText(comm['text'])
            ii += 1

        ii = 0
        for comm in comm_list:
            if comm['remove']: 
                self.node.remove(self.comments_list[ii].node)
                del self.comments_list[ii]
            ii += 1
    
    def getLanguage(self):
        return self.lang
    
    def setLanguage(self, lang):
        if lang != '':
            self.node.set('l', lang)
        elif 'l' in self.node.attrib:
            del self.node.attrib['l']
        self.lang = lang
        
    def getParent(self):
        return self.parent

    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        page_mark = ['','']
        html_str = u''
        if page_nr in self.pages:
            for el_obj in self.elements_list:
                html_str += el_obj.getHtmlVersion(page_nr, ed_level)
                if self.getWordsList()[0].getHtmlVersion(page_nr, ed_level) == '':
                    # There are words of this sentence in the previous page
                    page_mark[0] = "&#60;"
                if self.getWordsList()[len(self.getWordsList())-1].getHtmlVersion(page_nr, ed_level) == '':
                    # There are words of this sentence in the next page
                    page_mark[1] = "&#62;"
        if len(html_str.strip()) > 0:
            lang = ''
            type = ''
            comm = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = ':'+self.type
            if len(self.comments_list) > 0:
                comm = '<sub><font color="green" size="-2">+</font></sub>'
            if self.parent.node.tag != 'sce':
                html_str = u'<p><word id=' + self.getId() +\
                            '><font size="1" color="gray">['+page_mark[0]+'p'+page_mark[1]+type+lang+']</font></word>' + comm + ' ' +\
                            html_str + '</p>'
            else:
                 html_str = u'<word id=' + self.getId() +\
                            '><font size="1" color="gray">['+page_mark[0]+'p'+page_mark[1]+type+lang+']</font></word>' + comm + ' ' +\
                            html_str + '<br>'
        return html_str

    def getHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        page_mark = ['','']
        html_str = u''
        if page_nr in self.pages:
            for el_obj in self.elements_list:
                html_str += el_obj.getHtmlPOSVersion(page_nr, ed_level)
                if self.getWordsList()[0].getHtmlVersion(page_nr, ed_level) == '':
                    # There are words of this sentence in the previous page
                    page_mark[0] = "&#60;"
                if self.getWordsList()[len(self.getWordsList())-1].getHtmlVersion(page_nr, ed_level) == '':
                    # There are words of this sentence in the next page
                    page_mark[1] = "&#62;"
        if len(html_str.strip()) > 0:
            lang = ''
            type = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = ':'+self.type
            if self.parent.node.tag != 'sce':
                html_str = u'<p><word id=' + self.getId() +\
                            '><font size="1" color="gray">['+page_mark[0]+'p'+page_mark[1]+type+lang+']</font></word> ' +\
                            html_str + '</p>' 
            else:
                html_str = u'<word id=' + self.getId() +\
                            '><font size="1" color="gray">['+page_mark[0]+'p'+page_mark[1]+type+lang+']</font></word> ' +\
                            html_str + '<br>' 
        return html_str

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        ignore_list = []
        if __builtin__.cfg.get(u'Preferences', u'ElementTypes') != '':
            for p in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                while p.count('|') <= 2:
                    p += '|'
                el, desc, pos, css = p.split('|')
                if el == _(u'Parágrafo') and pos == _(u'ignorar'):
                    ignore_list.append(desc)
        return (self.getType() not in ignore_list and self.getLanguage() == '' and self.parent.isRelevantToPOS()) 
        
    def getWordsList(self):
        '''
        Returns a list of all the words in this paragraph.
        '''
        list = []
        for el in self.elements_list:
            list.extend(el.getWordsList())
        return list

    def exportToWordTagFormat(self, ed_level=["seg"], options=[], POS=True):
        '''
        Exports text in the word/TAG format (as the one read by CorpusSearch).
        '''
        text = u''
        if self.isRelevantToPOS():
            for el_obj in self.elements_list:
                text += el_obj.exportToWordTagFormat(ed_level,options,POS)
        elif 'PAGES' in options:
            # Pode haver quebras em elementos ignorados para exportação
            for wordObj in self.getWordsList():
                if wordObj.hasBreak('p'):
                    text += '<P_' + str(wordObj.containing_page+1) + '>/CODE\n\n'
            
        return text #+ '\n\n'

    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        # a. Some types of words are not relevant for linguistic analyses
        # b. Foreign words are not relevant for ling analyses
        if 'p:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '\n\n[page: ' + str(w_obj.containing_page) + ']\n\n'
            return text
        
        before = u''
        after = u''
        if 'PRINT_EL_TYPE' in options and len(self.getType()) > 0:
            before = u'[' + self.getType() + ':'
            after = ']'

        text = u''
        for el_obj in self.elements_list:
            text += el_obj.exportToText(ed_level, options, ignore_list)

        text = before + text + after # + '\n\n'
        
        # Fix the [page] position
        text = re.sub(r' *(\n\n\[page[^\]]+\]\n\n)\]', r']\1', text)

        return text

    def exportToHtml(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        # a. Some types of words are not relevant for linguistic analyses
        # b. Foreign words are not relevant for ling analyses
        if 'p:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '<br/><br/>[page: ' + str(w_obj.containing_page) + ']<br/><br/>'
            return text
        
        before = u''
        after = u''
        f_type = u''
        if len(self.getType()) > 0:
            f_type = 'class="' + self.getType() + '"'
            if 'PRINT_EL_TYPE' in options:
                before += u'<span class="el_type_color">[</span><span class="el_type">' + self.getType() + '</span>'
                after = '<span class="el_type_color">]</span>'

        text = u''
        for el_obj in self.elements_list:
            text += el_obj.exportToHtml(ed_level, options, ignore_list)

        # Format
        f_aux = ''
        if self.isBold(): f_aux += 'font-weight:bold;'
        if self.isItalic(): f_aux = 'font-style:italic;'
        if self.isUnderlined(): f_aux = 'text-decoration:underline;'

        text = '<p ' + f_type + '>' + before + '<span style="' + f_aux + '">' + text + '</span>' + after + '</p>'
        
        # Fix the [page] position
        text = re.sub(r' *(<br/><br/>\[page[^\]]+\]<br/><br/></span></span>)<span class="el_type_color">\]</span>', r'<span class="el_type_color">]</span>\1', text)

        return text

    def getString(self):
        '''
        Returns the content of this object in a string format.
        '''
        text = u''
        for el_obj in self.elements_list:
            text += el_obj.getString()
        return text

    def setPage(self, page_nr):
        if page_nr not in self.pages:
            self.pages.append(page_nr)
            self.parent.setPage(page_nr)

    def adjustPages(self):
        self.pages = []
        for el_obj in self.elements_list:
            el_obj.adjustPages()
            for page in el_obj.pages:
                self.setPage(page)

    def getElementByRef(self, el_ref):
        '''
        Remove the element from the document.
        '''
        try:
            for el in self.elements_list:
                if el.node.get('id') == el_ref:
                    return el
        except:
            raise
        return None

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]

    def rebuild(self, node):
        '''
        Rebuild the Paragraph object based on the node specified.
        '''
        self.__init__(self.parent, node)


class TextElement():
    '''
    This class wraps the subtrees of the document, included between
    <te></te> and provides specific operations over its content.
    '''
    def __init__(self, parent, node):
        self.node = node
        self.parent = parent
        self.pages = []
        self.word = None
        self.type = ''
        if self.node.get('t') is not None:
            self.type = self.node.get('t') 
        for el in node.getchildren():
            if el.tag == 'w' and self.word is None:
                self.word = Word(self, el, el.get('id'))
            else:
                __builtin__.log(_(u"XML mal formado") + " (TextElement.__init__, id=" + str(el.get('id')) + ")\n")

    def getId(self):
        return self.node.get('id')

    def getType(self):
        return self.type
    
    def setType(self, type):
        if type.strip() != '':
            self.node.set('t', type)
        elif 't' in self.node.attrib:
            del self.node.attrib['t']
        self.type = type

    def getParent(self):
        return self.parent

    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        if self.word is not None:
            html_str += self.word.getHtmlVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            html_str = u'<center><word id=' + self.getId() +\
                        '><font size="1" color="gray">#</font></word>' +\
                        html_str + '</center>'
        return html_str

    def getHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        This element is not relevant for linguistic analyses.
        '''
        html_str = u''
        if self.word is not None:
            html_str += self.word.getHtmlPOSVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            html_str = u'<center><word id=' + self.getId() +\
                        '><font size="1" color="gray">#</font></word>' +\
                        html_str + '</center>'
        return html_str

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        return False 
        
    def getElements(self):
        '''
        Returns a list of all the words in this text-element.
        '''
        return self.getWordsList()

    def getElementByRef(self, el_ref):
        '''
        Remove the element from the document.
        '''
        if self.word.getId() == el_ref:
            return self.word
        return None

    def getWordsList(self):
        '''
        Returns a list of all the words in this text-element.
        '''
        list = []
        if self.word is not None:
            list.append(self.word)
        return list

    def rebuild(self, node):
        '''
        Rebuild the elements list, based on the node specified.
        '''
        #self.word = None
        for el in node.getchildren():
            if el.tag == 'w' and self.word is None:
                self.word = Word(self, el, el.get('id'))
            else:
                __builtin__.log(_(u"XML mal formado") + " (TextElement.__init__, id=" + str(el.get('id')) + ")\n")

    def exportToWordTagFormat(self, ed_level=["seg"], options=[], POS=True):
        '''
        Nothing to export.
        '''
        return u''

    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
        """
        if 'TOOLS_TEXT_ONLY' in options:
            if self.node.get('t') == 'pgn':
                return u'<P_' + self.word.exportToText(ed_level, options, []) + '> '
        else:
            return u'[p.' + self.word.exportToText(ed_level, options, []) + ']'

    def exportToHtml(self, ed_level, options=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
        """
        if 'TOOLS_TEXT_ONLY' in options:
            if self.node.get('t') == 'pgn':
                return u'&lt;P_' + self.word.exportToHtml(ed_level, options, []) + '&gt; '
        else:
            return u'<p align="center" style="padding: 2px; margin: 0px; font-size:10pt;">' +\
                    self.word.exportToHtml(ed_level, options, []) + '</p>'

    def getString(self):
        '''
        Returns the content of this object in a string format.
        '''
        if self.word is not None:
            return u'' + self.word.getString()
        return u''

    def setPage(self, page_nr):
        if page_nr not in self.pages:
            self.pages.append(page_nr)
            self.parent.setPage(page_nr)

    def adjustPages(self):
        self.pages = []
        if self.word is not None:
            self.setPage(self.word.containing_page)

    def removeWord(self, word):
        '''
        Remove a word object from the sentence list of words.
        '''
        self.node.remove(word.node)
        self.word = None
        # Remove the TextElement itself
        self.parent.remove(self)
        self.adjustPages()

    def isBold(self):
        return False
    
    def isItalic(self):
        return False
    
    def isUnderlined(self):
        return False


class SectionElement():
    '''
    This class wraps the subtrees of the document, included between
    <sce></sce> and provides specific operations over its content.
    '''
    def __init__(self, parent, node):
        self.node = node
        self.parent = parent
        self.pages = []
        self.elements_list = []
        self.type = ''
        if self.node.get('t') is not None:
            self.type = self.node.get('t')
        self.lang = '' 
        if self.node.get('l') is not None:
            self.lang = self.node.get('l')
        # Build objects
        for el in node.getchildren():
            el_obj = None
            if el.tag == 'te' and el.get('t') == 'pgn':
                el_obj = TextElement(self, el)
            elif el.tag == 'p':
                el_obj = Paragraph(self, el)
            else:
                __builtin__.log(_(u"XML mal formado") + " (SectionElement.__init__, id=" + str(el) + ' ' + str(el.get('id')) + ")\n")
            if el_obj is not None:
                self.elements_list.append(el_obj)
        # Apply the format defined to the subelements
        if node.get('f'):
            self.setFormat(node.get('f'))

    def setFormat(self, format):
        '''
        Apply the format defined to the section element to all of its
        children.
        '''
        for el in self.elements_list:
            if isinstance(el, (Paragraph)):
                el.setFormat(format)

    def getType(self):
        return self.type
    
    def setType(self, type):
        if type.strip() != '':
            self.node.set('t', type)
        elif 't' in self.node.attrib:
            del self.node.attrib['t']
        self.type = type

    def getLanguage(self):
        return self.lang
    
    def setLanguage(self, lang):
        if lang != '':
            self.node.set('l', lang)
        elif 'l' in self.node.attrib:
            del self.node.attrib['l']
        self.lang = lang
        
    def isBold(self):
        return (self.node.get('f') is not None and 'b' in self.node.get('f').split(',')) or self.parent.isBold()
    
    def isItalic(self):
        return (self.node.get('f') is not None and 'i' in self.node.get('f').split(',')) or self.parent.isItalic()
    
    def isUnderlined(self):
        return (self.node.get('f') is not None and 'u' in self.node.get('f').split(',')) or self.parent.isUnderlined()

    def getId(self):
        return self.node.get('id')

    def remove(self, el):
        '''
        Removes an element from the list.
        '''
        if el in self.elements_list:
            self.elements_list.remove(el)
            self.node.remove(el.node)
        if len(self.getWordsList()) == 0:
            self.parent.remove(self)
        self.adjustPages()

    def getParent(self):
        return self.parent

    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        if page_nr in self.pages:
            for el_obj in self.elements_list:
                html_str += el_obj.getHtmlVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            lang = ''
            type = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = self.type
            else:
                type = 'sce'
            html_str = u'<word id=' + self.getId() +\
                        '><font size="1" color="gray">['+type+lang+']</font></word><br>' +\
                        html_str
            if type != '':
                if html_str.endswith('<br>'):
                    html_str = html_str[0:len(html_str) - 5] 
                if type == 'header':
                    html_str += '<hr size=1 color="gray">'
                if type == 'footer':
                    html_str = '<hr size=1 color="gray">' + html_str
        return html_str

    def getHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML POS version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        lang = ''
        type = ''
        if self.lang != '':
            lang = ':'+self.lang
        if self.type != '':
            type = self.type
        else:
            type = 'sce'
        if page_nr in self.pages:
            for el_obj in self.elements_list:
                html_str += el_obj.getHtmlPOSVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            html_str = u'<word id=' + self.getId() +\
                        '><font size="1" color="gray">['+type+lang+']</font></word><br>' +\
                        html_str
            if type != '':
                if html_str.endswith('<br>'):
                    html_str = html_str[0:len(html_str) - 5] 
                if type == 'header':
                    html_str += '<hr size=1 color="gray">'
                if type == 'footer':
                    html_str = '<hr size=1 color="gray">' + html_str
        return html_str

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        return False 
        
    def getWordsList(self):
        '''
        Returns a list of all the words in this section-element.
        '''
        list = []
        for el in self.elements_list:
            list.extend(el.getWordsList())
        return list
    
    def getText(self):
        '''
        Return the text (if any), with special coding for word editions.
        Example: "Header exammmple@mod_example text@seg_te|xt".
        '''
        text = u''
        for w_obj in self.getWordsList():
            if w_obj.getParent().node.tag == 'te': continue
            w_text = w_obj.getOriginalString()
            if len(text) > 0 and w_obj.getParent().getParent().getWordsList()[0] == w_obj:
                w_text = '\n' + w_text
            if w_obj.isEdited():
                w_text += '@'
                ed_types = []
                if __builtin__.cfg.get(u'Preferences', u'EditionTypes') != '':
                    for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                        type, label = ed.split('|')
                        ed_types.append(type)
                for ed_type in ed_types:
                    if w_obj.isEdited(ed_type):
                        w_text += ed_type + '_' + w_obj.getEditedString(ed_type).strip().replace(' ','|')
                        
            text += w_text + ' '
        return text

    def exportToWordTagFormat(self, ed_level=["seg"], options=[], POS=True):
        '''
        Nothing to export.
        '''
        return u''

    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
        """
        if 'TOOLS_TEXT_ONLY' in options:
            # Only the page number
            text = u''
            for el_obj in self.elements_list:
                if self.node.get('t') in ['header','footer'] and\
                        isinstance(el_obj, (TextElement)):
                    text += el_obj.exportToText(ed_level, options)
            return text
        else:
            text = u'['+self.node.get('t')+':\n'
            for el_obj in self.elements_list:
                text += el_obj.exportToText(ed_level, options)
            return text.strip() + ']'

    def exportToHtml(self, ed_level, options=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
        """
        if 'TOOLS_TEXT_ONLY' in options:
            # Only the page number
            text = u''
            for el_obj in self.elements_list:
                if self.node.get('t') in ['header','footer'] and\
                        isinstance(el_obj, (TextElement)):
                    text += el_obj.exportToHtml(ed_level, options)
            return text
        else:
            if self.node.get('t') == 'footer':
                before = u'<div class="footer">'
                after = '</div>'
            else:
                before = '<div class="header">'
                after = '</div>'
               
            text = u''
            for el_obj in self.elements_list:
                text += el_obj.exportToHtml(ed_level, options)
                
            return before + text + after

    def getString(self):
        '''
        Returns the content of this object in a string format. If
        to_nlp is True, some elements are not processed.
        '''
        text = u''
        for el_obj in self.elements_list:
            text += el_obj.getString()
        return text

    def setPage(self, page_nr):
        if page_nr not in self.pages:
            self.pages.append(page_nr)
            self.parent.setPage(page_nr)

    def adjustPages(self):
        self.pages = []
        for el_obj in self.elements_list:
            el_obj.adjustPages()
            for page in el_obj.pages:
                self.setPage(page)

    def getElementByRef(self, el_ref):
        '''
        Remove the element from the document.
        '''
        try:
            for el in self.elements_list:
                if el.node.get('id') == el_ref:
                    return el
                tmp = el.getElementByRef(el_ref)
                if tmp is not None:
                    return tmp
        except:
            raise
        return None

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]

    
class Section():
    '''
    This class wraps the subtrees of the document, included between
    <sc></sc> and provides specific operations over its content.
    '''
    def __init__(self, parent, node):
        self.node = node
        self.parent = parent
        self.pages = []
        self.elements_list = []
        self.comments_list = []
        self.type = ''
        if self.node.get('t') is not None:
            self.type = self.node.get('t')
        self.lang = '' 
        if self.node.get('l') is not None:
            self.lang = self.node.get('l') 
        # Process comments elements
        for comm in node.findall('comment'):
            c_obj = Comment(self, comm)
            self.comments_list.append(c_obj)
        # Process other elements
        for el in node.getchildren():
            el_obj = None
            if el.tag == 'sce':
                # Fix XML to the new approach (only Header/Footer will remain as SectionElements)
                if el.get('t') in ['header','footer']:
                    child_list = el.getchildren()
                    if len(child_list) > 0 and child_list[0].tag == 's':
                        p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
                        __builtin__.ids['p'] += 1
                        while len(child_list) > 0 and child_list[0].tag == 's':
                            p_el.append(child_list[0])
                            child_list = el.getchildren()
                        el.insert(0, p_el)
                    if len(child_list) > 0 and child_list[-1].tag == 's':
                        p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
                        __builtin__.ids['p'] += 1
                        while len(child_list) > 0 and child_list[-1].tag == 's':
                            p_el.insert(0, child_list[-1])
                            child_list = el.getchildren()
                        el.append(p_el)
                    el_obj = SectionElement(self, el)
                else:
                    el.tag = 'p'
                    el_obj = Paragraph(self, el)
            elif el.tag == 'p':
                el_obj = Paragraph(self, el)
            elif el.tag != 'comment':
                __builtin__.log(_(u"XML mal formado") + " (Section.__init__, id=" + str(el.get('id')) + ',' +\
                                str(el) + str(el.attrib) + ')\n')
            if el_obj is not None:
                self.elements_list.append(el_obj)
        # Apply the format defined to the subelements
        if node.get('f'):
            self.setFormat(node.get('f'))
            
    def getParent(self):
        return self.parent
    
    def setFormat(self, format):
        '''
        Apply the format defined to the section element to all of its
        children.
        '''
        for el in self.elements_list:
            if isinstance(el, (SectionElement, Paragraph)):
                el.setFormat(format)

    def getType(self):
        return self.type
    
    def setType(self, type):
        if type.strip() != '':
            self.node.set('t', type)
        elif 't' in self.node.attrib:
            del self.node.attrib['t']
        self.type = type

    def getComments(self):
        comm_list = []
        for comm in self.comments_list:
            c = {}
            c['author'] = comm.getAuthor()
            c['date']   = comm.getDate()
            c['title']  = comm.getTitle()
            c['text']   = comm.getText()
            c['remove'] = False
            comm_list.append(c)
        return comm_list

    def setComments(self, comm_list):
        '''
        Set the comment elements for the object and its node.
        '''
        ii = 0
        for comm in comm_list:
            if not comm['remove']: 
                if ii >= len(self.comments_list):
                    comm_node = etree.SubElement(self.node, 'comment')
                    self.comments_list.append(Comment(self, comm_node))
                
                self.comments_list[ii].setAuthor(comm['author'])
                self.comments_list[ii].setDate(comm['date'])
                self.comments_list[ii].setTitle(comm['title'])
                self.comments_list[ii].setText(comm['text'])
            ii += 1

        ii = 0
        for comm in comm_list:
            if comm['remove']: 
                self.node.remove(self.comments_list[ii].node)
                del self.comments_list[ii]
            ii += 1
    
    def getLanguage(self):
        return self.lang
    
    def setLanguage(self, lang):
        if lang != '':
            self.node.set('l', lang)
        elif 'l' in self.node.attrib:
            del self.node.attrib['l']
        self.lang = lang
        
    def isBold(self):
        return (self.node.get('f') is not None and 'b' in self.node.get('f').split(','))
    
    def isItalic(self):
        return (self.node.get('f') is not None and 'i' in self.node.get('f').split(','))
    
    def isUnderlined(self):
        return (self.node.get('f') is not None and 'u' in self.node.get('f').split(','))

    def getId(self):
        return self.node.get('id')

    def remove(self, el):
        '''
        Removes an element from the list.
        '''
        if el in self.elements_list:
            self.elements_list.remove(el)
            if el.node in self.node.getchildren():
                self.node.remove(el.node)
        if len(self.getWordsList()) == 0:
            self.parent.remove(self)
        self.adjustPages()

    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        if page_nr in self.pages:
            i = 0
            if isinstance(self.elements_list[0], SectionElement) and\
                    self.elements_list[0].node.get('t') == 'header':
                i = 1 # Ignores the header here
            for el_obj in self.elements_list[i:]:
                html_str += el_obj.getHtmlVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            lang = ''
            type = ''
            comm = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = ':'+self.type
            if len(self.comments_list) > 0:
                comm = '<sub><font color="green" size="-2">+</font></sub>'
            html_str = u'<word id=' + self.getId() +\
                        ' hint="Clique para alterar"><font size="1" color="gray">[section'+type+lang+']</font></word>' + comm + '<br> ' +\
                        html_str
        return html_str

    def getHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML POS version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        if page_nr in self.pages:
            i = 0
            if isinstance(self.elements_list[0], SectionElement) and\
                    self.elements_list[0].node.get('t') == 'header':
                i = 1 # Ignores the header here
            for el_obj in self.elements_list[i:]:
                html_str += el_obj.getHtmlPOSVersion(page_nr, ed_level)
        if len(html_str.strip()) > 0:
            lang = ''
            type = ''
            if self.lang != '':
                lang = ':'+self.lang
            if self.type != '':
                type = ':'+self.type
            html_str = u'<word id=' + self.getId() +\
                        ' hint="Clique para alterar"><font size="1" color="gray">[section'+type+lang+']</font></word><br> ' +\
                        html_str
        return html_str

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        ignore_list = []
        if __builtin__.cfg.get(u'Preferences', u'ElementTypes') != '':
            for p in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                while p.count('|') <= 2:
                    p += '|'
                el, desc, pos, css = p.split('|')
                if el == _(u'Seção') and pos == _(u'ignorar'):
                    ignore_list.append(desc)
        return (self.getType() not in ignore_list and self.getLanguage() == '') 

    def getPageHeader(self):
        '''
        Returns (if found) the header for the first page of the text.
        '''
        if isinstance(self.elements_list[0], SectionElement) and\
                self.elements_list[0].node.get('t') == 'header':
            return self.elements_list[0]
        return None

    def getPageFooter(self):
        '''
        Returns (if found) the footer for the last page of the text.
        '''
        if isinstance(self.elements_list[-1], SectionElement) and\
                self.elements_list[-1].node.get('t') == 'footer':
            return self.elements_list[-1]
        return None

    def getWordsList(self):
        '''
        Returns a list of all the words in this section.
        '''
        list = []
        for el in self.elements_list:
            list.extend(el.getWordsList())
        return list
    
    def exportToWordTagFormat(self, ed_level=["seg"], options=[], POS=True):
        '''
        Exports text in the word/TAG format (as the one read by CorpusSearch).
        '''
        text = u''
        if self.isRelevantToPOS():
            for el_obj in self.elements_list:
                text += el_obj.exportToWordTagFormat(ed_level,options,POS)
        elif 'PAGES' in options:
            # Pode haver quebras em elementos ignorados para exportação
            for wordObj in self.getWordsList():
                if wordObj.hasBreak('p'):
                    text += '<P_' + str(wordObj.containing_page+1) + '>/CODE\n\n'
        return text

    def exportToText(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to text.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        # Some types of words are not relevant for linguistic analyses
        if 'sc:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '\n\n[page: ' + str(w_obj.containing_page) + ']\n\n'
            return text
        
        before = u''
        if 'PRINT_EL_TYPE' in options:
            if len(self.getType()) > 0:
                before = u'[ ' + self.getType() + ' ]\n\n'
            else:
                before = u'[ section ]\n\n'

        pos = 0
        if self.elements_list[0].node.tag == 'sce': pos = 1 # Do not print the first header (again)

        max = len(self.elements_list)
        if self.elements_list[-1].node.tag == 'sce': max -= 1 # Do not print the last footer (again)
        
        text = u''
        for el_obj in self.elements_list[pos:max]:
            text += el_obj.exportToText(ed_level, options, ignore_list)

        text = before + text
    
        # Fix the [page] position
        text = re.sub(r' *(\n\n\[page[^\]]+\]\n\n)\]', r']\1', text)

        return text

    def exportToHtml(self, ed_level, options=[], ignore_list=[]):
        """
        Exports content to Html.
            options --> See Text.exportText()
            ignore_list --> Subtypes of elements to ignore 
        """
        # Some types of words are not relevant for linguistic analyses
        if 'sc:'+self.getType() in ignore_list or \
                ('TOOLS_TEXT_ONLY' in options and len(self.lang) > 0):
            # Check for possible page break
            text = u''
            for w_obj in self.getWordsList():
                # Page number
                if w_obj.getBreakType() == 'p':
                    text += '<br/><br/>[page: ' + str(w_obj.containing_page) + ']<br/><br/>'
            return text
        
        before = u''
        f_type = u''
        if len(self.getType()) > 0:
            f_type = self.getType()
            if 'PRINT_EL_TYPE' in options:
                before = u'<p><span class="el_type_color">[ ' + self.getType() + ' ]</span></p>'

        pos = 0
        if self.elements_list[0].node.tag == 'sce': pos = 1 # Do not print the first header (again)

        max = len(self.elements_list)
        if self.elements_list[-1].node.tag == 'sce': max -= 1 # Do not print the last footer (again)
        
        text = u''
        for el_obj in self.elements_list[pos:max]:
            text += el_obj.exportToHtml(ed_level, options, ignore_list)

        text = '<div ' + f_type + '>' + before + text + '</div>'
    
        # Fix the [page] position
        text = re.sub(r' *(<br/><br/>\[page[^\]]+\]<br/><br/>)\]', r']\1', text)

        return text

    def getString(self):
        '''
        Returns the content of this object in a string format. If
        to_nlp is True, some elements are not processed.
        '''
        text = u''
        for el_obj in self.elements_list:
            text += el_obj.getString()
        return text

    def setPage(self, page_nr):
        if page_nr not in self.pages:
            self.pages.append(page_nr)

    def adjustPages(self):
        self.pages = []
        for el_obj in self.elements_list:
            el_obj.adjustPages()
            for page in el_obj.pages:
                self.setPage(page)

    def getElementByRef(self, el_ref):
        '''
        Remove the element from the document.
        '''
        try:
            for el in self.elements_list:
                if el.node.get('id') == el_ref:
                    return el
                tmp = el.getElementByRef(el_ref)
                if tmp is not None:
                    return tmp
        except:
            raise
        return None

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]


class Break():
    '''
    This class wraps the break node element.
    '''
    def __init__(self, node):
        self.node = node
        self._build()
    
    def _build(self):
        self.elements_list = []
        for el in self.node.getchildren():
            el_obj = None
            if self.node.get('t') == 'l' and el.tag == 'te':
                el_obj = TextElement(self, el)
            elif self.node.get('t') == 'p' and el.tag == 'sce':
                # Fix XML to the new approach (only Header/Footer will remain as SectionElements)
                child_list = el.getchildren()
                if len(child_list) > 0 and child_list[0].tag == 's':
                    p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
                    __builtin__.ids['p'] += 1
                    while len(child_list) > 0 and child_list[0].tag == 's':
                        p_el.append(child_list[0])
                        child_list = el.getchildren()
                    el.insert(0, p_el)
                if len(child_list) > 0 and child_list[-1].tag == 's':
                    p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
                    __builtin__.ids['p'] += 1
                    while len(child_list) > 0 and child_list[-1].tag == 's':
                        p_el.insert(0, child_list[-1])
                        child_list = el.getchildren()
                    el.append(p_el)
                el_obj = SectionElement(self, el)
            else:
                __builtin__.log(_(u"XML mal formado") + " (Break.__init__, id=" + str(el.get('id')) + ")\n")
            if el_obj is not None:
                self.elements_list.append(el_obj)
                
    def rebuild(self, node):
        self.node = node
        self._build()

    def getParent(self):
        return None
    
    def getId(self):
        return self.node.get('id')

    def remove(self, el):
        '''
        Removes an element from the list.
        '''
        if el in self.elements_list:
            self.elements_list.remove(el)
            self.node.remove(el.node)

    def exportToText(self, el_type, ed_level, options=[], ignore_list=[]):
        '''
        Export content as text.
            el_type --> header / footer
            options --> See Text.exportText()
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == el_type:
                    text += el.exportToText(ed_level, options)
        return text

    def exportToHtml(self, el_type, ed_level, options=[]):
        '''
        Export content as Html.
            el_type --> header / footer
            options --> See Text.exportText()
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == el_type:
                    text += el.exportToHtml(ed_level, options)
        return text
            
    def getFooterHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for this element.
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'footer':
                    text += el.getHtmlVersion(page_nr, ed_level) + '<br>'
        return text

    def getFooterHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for this element.
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'footer':
                    text += el.getHtmlPOSVersion(page_nr, ed_level) + '<br>'
        return text

    def isRelevantToPOS(self):
        '''
        Return True if this word is relevant for POS tagging.
        '''
        return False 

    def getHeaderHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for this element.
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'header':
                    text += el.getHtmlVersion(page_nr, ed_level) + '<br>'
        return text

    def getHeaderHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for this element.
        '''
        text = u''
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'header':
                    text += el.getHtmlPOSVersion(page_nr, ed_level) + '<br>'
        return text
    
    def getWordsList(self):
        '''
        Returns a list of all the words in this element.
        '''
        list = []
        for el in self.elements_list:
            list.extend(el.getWordsList())
        return list

    def getFooterWordsList(self):
        '''
        Returns a list of all the words in this footer section.
        '''
        list = []
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'footer':
                    list.extend(el.getWordsList())
        return list

    def getHeaderWordsList(self):
        '''
        Returns a list of all the words in this header section.
        '''
        list = []
        if self.node.get('t') == 'p':
            for el in self.elements_list:
                if el.node.tag == 'sce' and el.node.get('t') == 'header':
                    list.extend(el.getWordsList())
        return list

    def getText(self, opt=0):
        '''
        Return the text (if any), with special coding for word editions.
        Example: "Header exammmple@mod_example text@seg_te|xt".
            opt --> 0.Header  1.Footer
        '''
        text = u''
        words_list = [self.getHeaderWordsList(), self.getFooterWordsList()][opt]
        for w_obj in words_list:
            if w_obj.getParent().node.tag == 'te': continue
            w_text = w_obj.getOriginalString()
            if len(text) > 0 and w_obj.getParent().getParent().getWordsList()[0] == w_obj:
                w_text = '\n' + w_text
            if w_obj.isEdited():
                w_text += '@'
                ed_types = []
                if __builtin__.cfg.get(u'Preferences', u'EditionTypes') != '':
                    for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                        type, label = ed.split('|')
                        ed_types.append(type)
                for ed_type in ed_types:
                    if w_obj.isEdited(ed_type):
                        w_text += ed_type + '_' + w_obj.getEditedString(ed_type).strip().replace(' ','|')
                        
            text += w_text + ' '
        return text
    
    def setPage(self, page_nr):
        pass

    def adjustPages(self):
        for el_obj in self.elements_list:
            el_obj.adjustPages() 

    def getElementByRef(self, el_ref):
        '''
        Remove the element from the document.
        '''
        try:
            for el in self.elements_list:
                if el.node.get('id') == el_ref:
                    return el
                tmp = el.getElementByRef(el_ref)
                if tmp is not None:
                    return tmp
        except:
            raise
        return None

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]

    def isBold(self):
        return False
    
    def isItalic(self):
        return False
    
    def isUnderlined(self):
        return False


class Comment():
    '''
    This class wraps the comment node element.
    '''
    def __init__(self, parent, node):
        self.node = node
        self.parent = parent

    def getAuthor(self):
        if self.node.get('author'):
            return self.node.get('author')
        return ''

    def setAuthor(self, value):
        self.node.set('author', value)

    def getDate(self):
        if self.node.get('date'):
            return self.node.get('date')
        return ''

    def setDate(self, value):
        self.node.set('date', value)

    def getTitle(self):
        if self.node.get('title'):
            return self.node.get('title')
        return ''

    def setTitle(self, value):
        self.node.set('title', value)

    def getText(self):
        if self.node.text:
            return self.node.text
        return ''

    def setText(self, value):
        self.node.text = value
    

class Text():
    '''
    This class wraps the subtrees of the document, included between
    <text></text> and provides specific operations over its content.
    '''
    def __init__(self, node):
        self.node = node
#        print 'text build',
#        t = time.time()
        self._build()
#        t = time.time() - t
#        print t
        
    def _build(self):
        '''
        Build the document class structure and the pages list.
        '''
        self.elements_list = []
        self.comments_list = []
        self.sc_dict = {}
        self.p_dict = {}
        self.s_dict = {}
        self.sce_dict = {}
        self.te_dict = {}
        self.bk_dict = {}
        self.words_dict = {}
        self.words_list = []
        self.words_id = []
        self.pages_list = []
        self.duplicates = {}
        # Process comments elements
        for comm in self.node.findall('comment'):
            c_obj = Comment(self, comm)
            self.comments_list.append(c_obj)
        # Process section elements
        for section in self.node.findall('sc'):
            section_obj = Section(self, section)
            self.elements_list.append(section_obj)
            # Insert each word of the section in the word lists
            for word in section_obj.getWordsList():
                self.words_id.append(word.getId())
                self.words_list.append(word)
                self.words_dict[word.getId()] = word
        if len(self.elements_list) > 0:
            # Generate lists of each kind of element (sc, p, s, sce, te)
            self.buildObjectLists(self.elements_list)
            # Process page breaks
            self.processPages()
            # Creates list of duplicate words (to be used in Replace All)
            self.updateDuplicates()
            # Update 'words' property
            self.node.set('words', str(len(self.words_list)))

    def buildObjectLists(self, obj_list):
        ''' Builds the list of objects for each type (sc, p, s, sce, te) '''
        for obj in obj_list:
            aux = eval('self.'+__builtin__.el_type_dict[obj.__class__.__name__])
            aux[obj.getId()] = obj
            if not isinstance(obj, (Sentence, TextElement)):
                self.buildObjectLists(obj.elements_list)

    def excludeFromObjectLists(self, obj):
        ''' Remove the element and its descendants from the lists of objects for each type (sc, p, s, sce, te) '''
        aux = eval('self.'+__builtin__.el_type_dict[obj.__class__.__name__])
        if obj.getId() in aux:
            del aux[obj.getId()]
        if not isinstance(obj, (Sentence, TextElement)):
            for child_obj in obj.elements_list:
                self.excludeFromObjectLists(child_obj)
        
    def updateDuplicates(self):
        '''
        Rebuild the duplicate words list.
        '''
        # Creates list of duplicate words (to be used in Replace All)
        self.duplicates = {}
        for w in self.words_list:
            self.insertDuplicate(w.getOriginalString(),w.getId())
        
#        f_dup = open('/tmp/dup.txt','w')
#        for key, value in self.duplicates.iteritems():
#            f_dup.write('['+key+']')
#            for w_id in value:
#                f_dup.write(' ('+w_id+','+self.words_dict[w_id].getOriginalString()+')')
#            f_dup.write('\n')
#        f_dup.close()
    
    def removeDuplicate(self, word_text, word_id):
        '''
        Remove ID from duplicates list.
        '''
        if word_text in self.duplicates and\
                word_id in self.duplicates[word_text]:
            self.duplicates[word_text].remove(word_id)
            if len(self.duplicates[word_text]) == 0:
                del self.duplicates[word_text]
        else:
            __builtin__.log(_(u'Aviso!') + ' [duplicate not found] [word:' + word_text + '] [id:' + word_id + ']\n')

    def insertDuplicate(self, word_text, word_id):
        '''
        Insert ID into the duplicates list.
        '''
        if word_text not in self.duplicates:
            self.duplicates[word_text] = []
        
        if word_id not in self.duplicates[word_text]:
            self.duplicates[word_text].append(word_id)
        else:
            __builtin__.log(_(u'Aviso!') + ' [duplicate already on list] [word:' + word_text + '] [id:' + word_id + ']\n')
    
    def processPages(self):
        '''
        Process pages, building a list of tuples with the following information for each page:
            (page_first_word_id, page_last_word_id, page_break_page_obj)
        The page_break_page_obj may be None.
        '''
        # First, exclude words from the old header and footer (if any)
        for p in self.pages_list:
            if p[2] is not None:
                bk_obj = p[2]
                for word in bk_obj.getFooterWordsList():
                    if word.getId() in self.words_id:
                        self.words_list.pop(self.words_id.index(word.getId()))
                        del self.words_dict[word.getId()]
                        self.words_id.remove(word.getId())
                        self.removeDuplicate(word.getOriginalString(),word.getId())
                # Process words from the header (to be in the next page)
                for word in bk_obj.getHeaderWordsList():
                    if word.getId() in self.words_id:
                        self.words_list.pop(self.words_id.index(word.getId()))
                        del self.words_dict[word.getId()]
                        self.words_id.remove(word.getId())
                        self.removeDuplicate(word.getOriginalString(),word.getId())
                # Remove from lists of each kind of element (sc, p, s, sce, te)
                self.excludeFromObjectLists(bk_obj)

        self.pages_list = []
        pages = self.node.getiterator('bk')
        i = 0
        for p in pages:
            if p.iterancestors(tag='w') is not None:
                if p.get('t') == 'p':
                    f = len(self.words_id) - 1
                    w_obj = self.words_list[-1]
                    for w in p.iterancestors(tag='w'):
                        f = self.words_id.index(w.get('id'))
                        w_obj = self.words_list[f]
                        break
                    bk_obj = Break(p)
                    self.bk_dict[bk_obj.getId()] = bk_obj  # Update list
                    # Generate lists of each kind of element (sc, p, s, sce, te)
                    self.buildObjectLists(bk_obj.elements_list)
                    tmp_list = [w_obj]
                    # Process words from the footer (to be in this page)
                    aux_list = bk_obj.getFooterWordsList()
                    if len(aux_list) > 0:
                        tmp_list.extend(aux_list)
                        self.updateWordLists([tmp_list[0]], tmp_list)
                        tmp_list = [aux_list[-1]]
                        f += len(aux_list)
                    # Process words from the header (to be in the next page)
                    aux_list = bk_obj.getHeaderWordsList()
                    if len(aux_list) > 0:
                        tmp_list.extend(aux_list)
                        self.updateWordLists([tmp_list[0]], tmp_list)
                    pos = f + len(aux_list) + 1
                    self.pages_list.append((self.words_id[i], self.words_id[f], bk_obj))
                    for ii in range(i, f + 1):
                        self.words_list[ii].setPage(len(self.pages_list))
                    i = f + 1
                elif p.get('t') == 'l':
                    # TODO: should treat the te[ln]?
                    pass
            else:
                __builtin__.log(_(u"XML fora do padrão: <bk> fora de <w> (p=") + str(page_nr) + ").\n")

        if i < len(self.words_id):
            self.pages_list.append((self.words_id[i], self.words_id[len(self.words_id) - 1], None))
        for ii in range(i, len(self.words_id)):
            self.words_list[ii].setPage(len(self.pages_list))
        self.last_page = len(self.pages_list)
        self.adjustPages()

    def adjustPages(self):
        for sec_obj in self.elements_list:
            sec_obj.adjustPages()

    def getComments(self):
        comm_list = []
        for comm in self.comments_list:
            c = {}
            c['author'] = comm.getAuthor()
            c['date']   = comm.getDate()
            c['title']  = comm.getTitle()
            c['text']   = comm.getText()
            c['remove'] = False
            comm_list.append(c)
        return comm_list

    def setComments(self, comm_list):
        '''
        Set the comment elements for the object and its node.
        '''
        ii = 0
        for comm in comm_list:
            if not comm['remove']: 
                if ii >= len(self.comments_list):
                    comm_node = etree.SubElement(self.node, 'comment')
                    self.comments_list.append(Comment(self, comm_node))
                
                self.comments_list[ii].setAuthor(comm['author'])
                self.comments_list[ii].setDate(comm['date'])
                self.comments_list[ii].setTitle(comm['title'])
                self.comments_list[ii].setText(comm['text'])
            ii += 1

        ii = 0
        for comm in comm_list:
            if comm['remove']: 
                self.node.remove(self.comments_list[ii].node)
                del self.comments_list[ii]
            ii += 1

    def getHtmlVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML version for the specified page element (a tuple
        containing the first and last words for the page).
        '''
        html_str = u''
        if page_nr > 1 and self.pages_list[page_nr-2][2] is not None:
            # Header
            html_str += self.pages_list[page_nr-2][2].getHeaderHtmlVersion(page_nr, ed_level)
        elif page_nr == 1:
            if self.elements_list[0].getPageHeader() is not None:
                html_str += self.elements_list[0].getPageHeader().getHtmlVersion(page_nr, ed_level)
        sec = 0
        for section_obj in self.elements_list:
            # Body of the page
            sec_text = section_obj.getHtmlVersion(page_nr, ed_level)
            if sec_text.strip() != '':
                if sec > 0:
                    html_str += '<br><br><font color="#cfcfcf" size="-2">--------------------: ' +\
                                _(u'quebra de seção') + ' :--------------------</font><br>'
                html_str += sec_text
                sec = 1
            
        if self.pages_list[page_nr-1][2] is not None:
            # Footer
            html_str += self.pages_list[page_nr-1][2].getFooterHtmlVersion(page_nr, ed_level)
        return html_str

    def getHtmlPOSVersion(self, page_nr, ed_level=[]):
        '''
        Get the HTML POS (part-of-speech) version for the specified page 
        element (a tuple containing the first and last words for the page).
        '''
        html_str = u''
        if page_nr > 1 and self.pages_list[page_nr-2][2] is not None:
            # Header
            html_str += self.pages_list[page_nr-2][2].getHeaderHtmlPOSVersion(page_nr, ed_level)
        elif page_nr == 1:
            if self.elements_list[0].getPageHeader() is not None:
                html_str += self.elements_list[0].getPageHeader().getHtmlPOSVersion(page_nr, ed_level)
        sec = 0
        for section_obj in self.elements_list:
            # Body of the page
            sec_text = section_obj.getHtmlPOSVersion(page_nr, ed_level)
            if sec_text.strip() != '':
                if sec > 0:
                    html_str += '<br><br><font color="#cfcfcf" size="-2">--------------------: ' +\
                                _(u'quebra de seção') + ' :--------------------</font><br>'
                html_str += sec_text
                sec = 1
            
        if self.pages_list[page_nr-1][2] is not None:
            # Footer
            html_str += self.pages_list[page_nr-1][2].getFooterHtmlPOSVersion(page_nr, ed_level)
        return html_str

    def getId(self):
        if self.node.get('id'):
            return self.node.get('id')
        return ''
        
    
    def getTitle(self):
        if self.node.get('title'):
            return self.node.get('title')
        else:
            return self.node.get('id')+u'[sem título]' 

    def getAuthor(self):
        if self.node.get('author'):
            return self.node.get('author')
        return '' 

    def getBorn(self):
        if self.node.get('born'):
            return self.node.get('born')
        return '' 

    def getType(self):
        if self.node.get('t'):
            return self.node.get('t')
        return '' 

    def getWordsDict(self):
        return self.words_dict

    def getWordsList(self):
        return self.words_list
    
    def getWordsId(self):
        return self.words_id
    
    def getPagesList(self):
        return self.pages_list
    
    def getWordByRef(self, ref):
        '''
        Returns the related Word object.
        '''
        try:
            pos = self.words_id.index(ref)
            return self.words_list[pos]
        except:
            return None
        
    def mergeToNextWord(self, word, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Merge the current word with the immediate next one and
        delete the next word.
        '''
        next_w = self.getNextWord(word, not isinstance(word.getParent().getParent().getParent(), SectionElement))
        if next_w is not None:
            if word.hasBreak() and next_w.hasBreak():
                __builtin__.log(_(u'Erro! Duas palavras com quebras de linha, página ou coluna não podem ser unidas.')+'\n')
                return False, _(u'Erro! Duas palavras com quebras de linha, página ou coluna não podem ser unidas.')
            if undo_stack is not None:
                undo_stack.insert(0, ['REMOVE_W', next_w, next_w.node.__deepcopy__(False),
                                      next_w.getParent().getElements().index(next_w),
                                      next_w.node.getparent().index(next_w.node), undo_text, undo_pg, 
                                      _(u'Desfazer exclusão de palavra.')])
            # If there is a break element in the next word, bring it to the current one
            #if next_w.node.find('o').find('bk') is not None:
            #    word.node.find('o').append(next_w.node.find('o').find('bk'))
            word.setOriginalString(word.getOriginalString('|') + ' ' + next_w.getOriginalString('|'), next_w.node.find('o').find('bk'))
            if next_w.node.getparent().tag in ['s','te']:
                s_el = next_w.node.getparent()
                s_id = s_el.get('id')
                # Update pages list
                # Case 1: the next word is the first of the next page
                if word.containing_page != next_w.containing_page:
                    p = self.pages_list[next_w.containing_page-1]
                    self.pages_list[next_w.containing_page-1] = (self.getNextWord(next_w, True).getId(), p[1], p[2])
                # Case 2: the next word is the last of the current page
                if self.pages_list[next_w.containing_page-1][1] == next_w.getId():
                    p = self.pages_list[next_w.containing_page-1]
                    self.pages_list[next_w.containing_page-1] = (p[0], word.getId(), p[2])
                # Update words list
                self.removeWord(next_w)
            else:
                __builtin__.log(_(u"Erro: não foi possível excluir a palavra da sentença.")+'\n')
                return False, _(u"Erro: não foi possível excluir a palavra da sentença.")
        return True, ''

    def unmergeToNextWord(self, word, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Unmerge the current word based on the the original string
        words (separated by whitespace).
        '''
        words_list = word.getOriginalString('|').split(' ')
        if len(words_list) > 1:
            w_or_text = words_list.pop(0)
            if word.node.getparent().tag in ['s','te']:
                s_el = word.node.getparent()
                s_id = s_el.get('id')
                # Insert splitted words in the sentence
                iword = s_el.index(word.node) + 1
                pos = self.words_id.index(word.getId())
                l_obj = word
                for w in words_list:
                    w_el = s_el.makeelement('w', id=str(__builtin__.ids['w'])) #s_id+'#'+str(iword))
                    __builtin__.ids['w'] += 1
                    or_el = etree.SubElement(w_el, 'o') #, id=w_el.get('id')+'#o')
                    or_el.text = w.split('|')[0]
                    # Process break element
                    if w.find('|') > -1:
                        bk_el = word.node.find('o').find('bk')
                        or_el.append(bk_el)
                        bk_el.tail = w.split("|")[1]
                        w = w.replace('|','')
                                                
                    s_el.insert(iword, w_el)
                    iword += 1
                # Words list to be updated
                old_list = word.getParent().getWordsList()
                # Redefine words (and its children) IDs
                #self.updateSentenceWordsIDs(s_el)
                # Update list before changing original word string
                self.removeDuplicate(word.getOriginalString(''),word.getId())
                # Change orginal string
                word.setOriginalString(w_or_text)
                # Rebuild parent (Sentence/TextElement) Words list
                word.getParent().rebuild(s_el)
                # Update word lists based on new Sentence object
                self.updateWordLists(old_list, word.getParent().getWordsList())
                # Undo
                if undo_stack is not None:
                    next_w = self.getNextWord(word, not isinstance(word.getParent().getParent().getParent(), SectionElement))
                    undo_stack[0][2].append(next_w) 
                self.processPages()
            else:
                __builtin__.log(_(u"Erro: não foi possível separar a palavra.\n"))
                return False
        return True

    def getNextWord(self, word, jun=False):
        '''
        Returns the next (following) Word object for a given Word or
        None if it is the last word of the document.
        
        jun --> True: ignore particular elements (TextElement, SectionElement)
        '''
        try:
            pos = self.getWordsId().index(word.getId()) + 1
            if jun:
                while pos < len(self.getWordsList()) and\
                        (isinstance(self.getWordsList()[pos].getParent(), TextElement) or\
                         isinstance(self.getWordsList()[pos].getParent().getParent().getParent(), SectionElement)):
                    pos += 1
            return self.getWordsList()[pos]
        except:
            return None

    def getPreviousWord(self, word, jun=False):
        '''
        Returns the next (preceding) Word object for a given Word or
        None if it is the first word of the document.
        
        jun --> True: ignore particular elements (TextElement, SectionElement)
        '''
        pos = self.getWordsId().index(word.getId()) - 1
        if jun:
            while pos >= 0 and\
                    (isinstance(self.getWordsList()[pos].getParent(), TextElement) or\
                     isinstance(self.getWordsList()[pos].getParent().getParent().getParent(), SectionElement)):
                pos -= 1
        try:
            if pos < 0: raise
            return self.getWordsList()[pos]
        except:
            return None
    
    def getWordContainingPage(self, word):
        '''
        Returns the number of the page that includes the specified
        word (returns page 1 if not found).
        '''
        return word.containing_page
    
    def getWordDuplicatesIDsList(self, word):
        '''
        Return the list of (following) duplicate words for the current one.
        '''
        tmp = {}
        try:
            for w_id in self.duplicates[word.getOriginalString()]:
                key = "%06d"%(self.words_id.index(w_id))
                tmp[key] = w_id
        except:
            __builtin__.log(_(u'Erro!') + ' [word:' + word.getOriginalString() + '] [id:' + word.getId() + '] [dup-list:' +\
                            str(self.duplicates) + ']\n')
        # Sort words by its position in the text (ascendent)
        ord_k = sorted(tmp.keys())
        # Start
        start = 0
        key = "%06d"%(self.words_id.index(word.getId()))
        if key in ord_k:
            start = ord_k.index(key) + 1
        else:
            __builtin__.log(_(u'Erro') + ' [getWordDuplicatesList()]:' + word.getId() + ' ' + str(word) + ' ' +\
                            self.duplicates[word.getOriginalString()])
        rt = []
        for k in ord_k[start:]:
            rt.append(tmp[k])
        return rt

    def updateWordLists(self, old_list, new_list):
        '''
        Update the general word lists based on an old list (words of
        a sentence/text-element) and a new (after updates) one.
        '''
        words_id = []
        words_list = []
        # Remove from duplicates list (to later insert the new ones)
        for w in old_list:
            self.removeDuplicate(w.getOriginalString(),w.getId())
            if w.getId() in self.words_dict:
                del self.words_dict[w.getId()]
            else:
                __builtin__.log(_(u'Aviso! Palavra não encontrada (')+w.getId()+':'+w.getOriginalString()+'). [updateWordLists]\n')
        # Index range of the words of the sentence in the current 
        #    lists
        first_w = self.words_id.index(old_list[0].getId())
        last_w = self.words_id.index(old_list[len(old_list) - 1].getId())
        # Process each word
        for word in new_list:
            words_id.append(word.getId())
            words_list.append(word)
            # Update directly in the dictionary
            self.words_dict[word.getId()] = word
            self.insertDuplicate(word.getOriginalString(),word.getId())
        # Replace the old range for the new elements
        self.words_id[first_w:last_w + 1] = words_id
        self.words_list[first_w:last_w + 1] = words_list

    def insertPageNumber(self, page_nr, page_pos, number, undo_stack=None, undo_text=None):
        '''
        Insert 'number' in the page header/footer. Parameters:
            page_nr  --> Current page under edition
            page_pos --> 0. Header   1.Footer
            number   --> Number to be inserted
            undo_stack --> Stack for undo information
        '''
        w_el = etree.Element('w')
        or_el = etree.SubElement(w_el, 'o')
        or_el.text = number
        w_obj = Word(None, w_el, '')
        
        if undo_stack is not None:
            undo_stack.insert(0,['INS_PG_NUM', w_el, page_pos, False,
                                 undo_text, page_nr, _(u'Desfazer inserção de número de página.')])
            
        return self.setWordAsPageNumber(w_obj, page_pos == 1, undo_stack, undo_text, page_nr)
                
    def setWordAsPageNumber(self, word, is_footer, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Transform the word under edition in a Page Number element
        (<te t="pgn">), insert it in a header/footer and in a page break (if needed).
        '''
        if word.getParent() is None:
            s_obj = None # No sentence to update
            p_obj = None
            prev_word = None
            next_word = None
            if not is_footer: 
                # header
                if undo_pg > 1:
                    # Break element is in the previous page last word
                    ref_word = self.getPageWords(undo_pg - 1)[-1]
                else:
                    # First page
                    ref_word = self.getPageWords(undo_pg)[0]
            else:
                ref_word = self.getPageWords(undo_pg)[-1]
                
            secel_el= None
            # 1: a page number element already exists
            if ref_word.getParent().node.tag == 'te':
                higher_el = ref_word.getParent().getParent().node.getparent() # <bk>
            # 2: a footer/header element already exists
            elif isinstance(ref_word.getParent().getParent().getParent(), SectionElement):
                higher_el = ref_word.getParent().getParent().getParent().node.getparent() # <bk>
            # 3: first/last (non-special, see 'getPrevisousWord()') word of the page
            else:
                # a: a break element already exists
                if ref_word.getOriginalString('|').find('|') >= 0:
                    higher_el = ref_word.node.find('o').find('bk') # <bk>
                # b: a initial/final SectionElement must be created
                else:
                    higher_el = ref_word.getParent().getParent().getParent().node # <sc>
                p_obj = ref_word.getParent().getParent()
        else:
            if word.getParent().node.tag == 'te':
                # Nothing to do!
                return False
            word.setFocused(False)

            s_obj = word.getParent()
            p_obj = s_obj.getParent()

            # Forbiden: Section to become empty
            if word.getParent().getParent().getParent().node.tag == 'sc' and\
                   len(word.getParent().getParent().getParent().getWordsList()) == 1:
                raise BaseException, _(u"Alerta: Seção não pode ficar vazia.")

            if undo_stack is not None:
                undo_stack.insert(0,['PG_NUM', s_obj, s_obj.node.__deepcopy__(False),
                                     p_obj.elements_list.index(s_obj),
                                     p_obj.node.index(s_obj.node), (word.getId(), is_footer),
                                     None, None, False, None, undo_text, undo_pg, _(u'Desfazer número de página.')])

            if isinstance(word.getParent().getParent().getParent(), SectionElement):
                # <sc> or <bk> node (word being converted is inside header/footer)
                higher_el = word.getParent().getParent().getParent().node.getparent()
                secel_el = word.getParent().getParent().getParent().node
                prev_word = None
                next_word = None
            else:
                prev_word = self.getPreviousWord(word, True)
                next_word = self.getNextWord(word, True)
                if prev_word is None or next_word is None:
                    # Header of first page or Footer of last: SEC_EL will be inserted right inside SEC
                    higher_el = p_obj.getParent().node
                else:
                    # Forbiden: two adjacent page number elements
                    if prev_word.getParent().getParent().node.get('t') == word.getParent().getParent().node.get('t') and\
                            prev_word.getParent().node.tag == 'te' and prev_word.getParent().node.get('t') == 'pgn':
                        if undo_stack is not None: undo_stack.pop(0)
                        raise BaseException, _(u"Alerta: Não é possível haver números de página consecutivos, sem texto entre eles. Neste caso, um dos elementos deverá ser excluído.")
                    # Undo information
                    if undo_stack is not None:
                        undo_stack[0][9] = ['W-EDIT', 
                                            [(prev_word, prev_word.node.__deepcopy__(False),
                                              prev_word.getParent().elements_list.index(prev_word),
                                              prev_word.node.getparent().getchildren().index(prev_word.node))],
                                            [], undo_text, undo_pg, _(u'Desfazer edição de palavra.')]
                    # A (possible) break inside the current word must be moved to the previous one 
                    higher_el = word.node.find('o').find('bk')
                    if higher_el is None:
                        # Check for a break element inside the previous word
                        higher_el = prev_word.node.find('o').find('bk')
                    if higher_el is None:
                        # Create a break element (as a last resort)
                        higher_el = etree.SubElement(prev_word.node.find('o'), 'bk', id='bk_'+str(__builtin__.ids['bk']), t='p')
                        __builtin__.ids['bk'] += 1
                    else:
                        id = higher_el.get('id')
                        # Removes prior footer/header
                        if higher_el.get('t') != 'p':
                            higher_el.clear()
                        higher_el.set('id', id)
                        higher_el.set('t', 'p')
                        prev_word.node.find('o').append(higher_el)
                # Creates the sce[header/footer] element
                secel_el = None

        if secel_el is None:
            if is_footer:
                for secel_el in higher_el.getchildren():
                    if secel_el.tag == 'sce' and secel_el.get('t') == 'footer':
                        break
                if secel_el is None or not (secel_el.tag == 'sce' and secel_el.get('t') == 'footer'):
                    secel_el = etree.Element('sce', id='sce_'+str(__builtin__.ids['sce']), t='footer')
                    __builtin__.ids['sce'] += 1
                    if higher_el.tag == 'sc':
                        higher_el.append(secel_el)
                    else:
                        higher_el.insert(0, secel_el)
            else:
                for secel_el in higher_el.getchildren():
                    if secel_el.tag == 'sce' and secel_el.get('t') == 'header':
                        break
                if secel_el is None or not (secel_el.tag == 'sce' and secel_el.get('t') == 'header'):
                    secel_el = etree.Element('sce', id='sce_'+str(__builtin__.ids['sce']), t='header')
                    __builtin__.ids['sce'] += 1
                    if higher_el.tag == 'bk':
                        higher_el.append(secel_el)
                    else:
                        higher_el.insert(0, secel_el)

        # Creates the te[page_nr] element
        text_el = secel_el.find('te')
        if text_el is None:
            text_el = etree.Element('te', id='te_'+str(__builtin__.ids['te']), t='pgn')
            __builtin__.ids['te'] += 1
        w_el = word.node.__deepcopy__(False)
        if undo_stack is not None and undo_stack[0][0] == 'INS_PG_NUM':
            undo_stack[0][1] = w_el
        if word.getParent() is not None: 
            word.node.getparent().remove(word.node)
        w_el.set('id', str(__builtin__.ids['w'])) #text_el.get('id')+'#0')
        __builtin__.ids['w'] += 1
        if text_el.find('w'):
            if undo_stack is not None and undo_stack[0][0] == 'INS_PG_NUM':
                # Undo must only replace the new node for the old one
                undo_stack[0][1] = text_el.getchildren()[0]
                undo_stack[0][3] = True
            text_el.remove(text_el.getchildren()[0])
        # Insert word_node in the TextElement node (and automatically remove it from the Sentence node)
        text_el.append(w_el)
        if is_footer:
            # Page number comes after footer text
            secel_el.append(text_el)
        else:
            # Page number comes befor footer text
            secel_el.insert(0, text_el)
        if prev_word is not None and prev_word.getOriginalString('|').find('|') < 0:
            prev_word.setOriginalString(prev_word.getOriginalString()+'|')
        if s_obj is not None:
            # Redefine words (and its children) IDs
            #self.updateSentenceWordsIDs(s_obj.node)
            # Update word lists based on new Sentence object
            old_list = s_obj.getWordsList()
            s_obj.rebuild(s_obj.node)
            self.updateWordLists(old_list, s_obj.getWordsList())
            # Undo information
            if undo_stack is not None:
                tmp = s_obj.getParent()
                if len(tmp.getWordsList()) == 0:
                    undo_stack[0][6] = [tmp, tmp.getParent().elements_list.index(tmp),
                                        tmp.node.getparent().getchildren().index(tmp.node), next_word]
            # Process the deletion recursively (if the parent become empty too)
            tmp = s_obj
            while len(tmp.getElements()) == 0:
                undo_stack[0][8] = True
                tmp.getParent().remove(tmp)
                tmp = tmp.getParent()
        # Update Section obj
        if higher_el.tag == 'sc':
            if p_obj is None:
                p_obj = word.getParent().getParent().getParent()

            secel_obj = SectionElement(p_obj.getParent(), secel_el)
            aux = eval('self.'+__builtin__.el_type_dict[secel_obj.__class__.__name__])
            aux[secel_obj.getId()] = secel_obj
            self.buildObjectLists(secel_obj.elements_list)

            # Undo information
            if undo_stack is not None and undo_stack[0][0] == 'PG_NUM':
                undo_stack[0][7] = secel_obj

            if is_footer:
                obj = p_obj.getParent().elements_list[-1]
            else:
                obj = p_obj.getParent().elements_list[0]

            if obj.node.tag == 'sce' and obj.node.get('t') == secel_el.get('t'):
                self.updateWordLists(obj.getWordsList(), [])
                self.excludeFromObjectLists(obj)
                p_obj.getParent().remove(obj)
            if is_footer:
                p_obj.getParent().elements_list.append(secel_obj)
                p_obj.getParent().node.append(secel_el)
                new_list = secel_obj.getWordsList()
                new_list.insert(0, self.words_list[-1])
                self.updateWordLists([self.words_list[-1]], new_list)
            else:
                p_obj.getParent().elements_list.insert(0, secel_obj)
                p_obj.getParent().node.insert(0,secel_el)
                new_list = secel_obj.getWordsList()
                new_list.append(self.words_list[0])
                self.updateWordLists([self.words_list[0]], new_list)
                    
        self.processPages()
        return True
    
    def getLastPageNumber(self):
        return self.last_page

    def getPageWords(self, num):
        '''
        Return sublist of words in page {num}.
        '''
        try:
            i = self.words_id.index(self.getPagesList()[num-1][0])
            f = self.words_id.index(self.getPagesList()[num-1][1])+1
            return self.getWordsList()[i:f]
        except:
            return []

    def remove(self, el):
        '''
        Removes an element from the list.
        '''
        if el in self.elements_list:
            self.elements_list.remove(el)
            self.node.remove(el.node)
        if el in self.comments_list:
            self.comments_list.remove(el)
            self.node.remove(el.node)
        
    def removeWord(self, word, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Remove word from the document.
        '''
        if word in word.getParent().getWordsList() or\
                (word.getOriginalString() == self.getWordByRef(word.getId()).getOriginalString()):

            word = self.getWordByRef(word.getId())
            
            tmp = word.getParent()
            if undo_stack is not None:
                undo_stack.insert(0, ['REMOVE_W', word, word.node.__deepcopy__(False),
                                      word.getParent().getElements().index(word),
                                      word.node.getparent().index(word.node), undo_text, undo_pg, 
                                      _(u'Desfazer exclusão de palavra.')])
                # Check whether a parent element will become empty (and be deleted)
                par_obj = None
                while len(tmp.getWordsList()) == 1 and not isinstance(tmp, Break):
                    par_obj = tmp
                    tmp = tmp.getParent()
                if par_obj is not None:
                    undo_stack[0] = ['EL-REMOVE', par_obj, par_obj.node.__deepcopy__(False),
                                     par_obj.getParent().getElements().index(par_obj),
                                     par_obj.node.getparent().index(par_obj.node), self.getPreviousWord(word),
                                     par_obj.getParent().getId(), undo_text, undo_pg, 
                                     _(u'Desfazer exclusão de elemento.')]
                    self.removeElementByRef(par_obj.getId())
                    return True
            # Exclude from word lists
            old_list = tmp.getWordsList()
            # Exclude from sentence
            tmp.removeWord(word)
            # Update lists
            self.updateWordLists(old_list, tmp.getWordsList())
            self.processPages()
            return True
        return False

    def moveWord(self, word, forward=True, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Move word forward (forward=True) or backward (forward=False).
        '''
        st = not (isinstance(word.getParent(), TextElement) or\
                  isinstance(word.getParent().getParent(), SectionElement))
             
        if (forward and self.getNextWord(word, st) is None) or\
                (not forward and self.getPreviousWord(word, st) is None):
            return word

        # Get the "future" parent for the word node
        if forward:
            s_obj = self.getNextWord(word, st).getParent()
            iword = s_obj.node.index(self.getNextWord(word, st).node)
            if word.getParent() != self.getNextWord(word, st).getParent():
                # Do not go on when word is meant to live/enter a TextElement
                if (isinstance(word.getParent(), TextElement) or isinstance(self.getNextWord(word, st).getParent(), TextElement)) and\
                         word.getParent().getParent() != self.getNextWord(word, st).getParent().getParent():
                    return word
                iword = 0
        else:
            s_obj = self.getPreviousWord(word, st).getParent()
            iword = s_obj.node.index(self.getPreviousWord(word, st).node)
            if word.getParent() != self.getPreviousWord(word, st).getParent():
                # Do not go on when word is meant to live/enter a TextElement
                if (isinstance(word.getParent(), TextElement) or isinstance(self.getPreviousWord(word, st).getParent(), TextElement)) and\
                         word.getParent().getParent() != self.getPreviousWord(word, st).getParent().getParent():
                    return word
                iword = len(self.getPreviousWord(word, st).getParent().getWordsList())

        # Remove word of its current position
        if not self.removeWord(word):
            return word

        if not word.getParent().getString().strip() == '':
            # Redefine sentence words (and its children) IDs
            #self.updateSentenceWordsIDs(word.getParent().node)
            # Update word lists based on new Sentence object
            old_list = word.getParent().getWordsList()
            word.getParent().rebuild(word.getParent().node)
            self.updateWordLists(old_list, word.getParent().getWordsList())

        # Insert word node in the new position
        s_obj.node.insert(iword, word.node)
        # Redefine sentence words (and its children) IDs
        #self.updateSentenceWordsIDs(s_obj.node)
        # Update word lists based on new Sentence object
        old_list = s_obj.getWordsList()
        s_obj.rebuild(s_obj.node)
        self.updateWordLists(old_list, s_obj.getWordsList())

        self.processPages()

        if undo_stack is not None:
            undo_stack.insert(0, ['MOVE_W', self.words_dict[word.node.get('id')], not forward, undo_text, undo_pg, 
                                  _(u'Desfazer "mover palavra".')])

        return self.words_dict[word.node.get('id')]
    
    def breakParagraph(self, word, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Breaks the current paragraph/section-element.
        '''
        w_id = word.getId()
        w_parent = word.node.getparent()
        w_parent_obj = word.getParent()
        w_node = word.node

        # Insert a new paragraph node after the current one
        par = w_parent.getparent()
        sec = par.getparent()
        pos = sec.getchildren().index(par) 
        p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
        __builtin__.ids['p'] += 1
        sec.insert(pos + 1, p_el)
        # Create Paragraph instance and insert in the Section too
        p_obj = word.getParent().getParent()

        if undo_stack is not None:
            undo_stack.insert(0, ['BK_P', p_obj, p_obj.node.__deepcopy__(False),
                                  p_obj.getParent().getElements().index(p_obj),
                                  p_obj.node.getparent().index(p_obj.node), undo_text, undo_pg, 
                                  _(u'Desfazer quebra de parágrafo')])

        sc_obj = p_obj.getParent()
        new_p_obj = Paragraph(sc_obj, p_el)
        sc_obj.elements_list.insert(sc_obj.elements_list.index(p_obj)+1, new_p_obj)
        
        # If the current word is not at the end of its sentence
        s_el = None 
        if w_parent.getchildren().index(word.node) < len(w_parent.getchildren()) - 1:
            s_el = etree.Element('s', id='s_'+str(__builtin__.ids['s']))
            __builtin__.ids['s'] += 1
            pos = w_parent.getchildren().index(word.node) + 1
            for w in w_parent.getchildren()[pos:]:
                s_el.append(w)
            # Redefine sentence words (and its children) IDs
            #self.updateSentenceWordsIDs(w_parent)
            #self.updateSentenceWordsIDs(s_el)
            # Word lists 
            old_list = w_parent_obj.getWordsList()
            w_parent_obj.rebuild(w_parent)
            s_obj = Sentence(new_p_obj, s_el)
            self.s_dict[s_obj.getId()] = s_obj
            new_list = w_parent_obj.getWordsList()
            new_list.extend(s_obj.getWordsList())
            self.updateWordLists(old_list, new_list)

        # Transfer the new sentence and the next ones to the new paragraph
        if s_el is not None:
            p_el.append(s_el)
            new_p_obj.elements_list.append(s_obj)
        pos = 1
        for s in p_obj.getElements():
            if s.node.get('id') == w_parent_obj.node.get('id'):
                break
            pos += 1 
        for s in p_obj.getElements()[pos:]:
            new_p_obj.elements_list.append(s)
            p_el.append(s.node)
            p_obj.elements_list.remove(s)
            s.parent = new_p_obj

        # Update ID lists
        self.p_dict[new_p_obj.getId()] = new_p_obj
        self.buildObjectLists(new_p_obj.elements_list)

        # Reprocess pages
        self.processPages()
        
        return self.getWordByRef(w_node.get('id'))

    def insertText(self, word, text, position, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Process a portion of text and create a XML structure for
        it. Then insert this structure in the current open XML
        document, right after the word under edition.
        
            position --> 0. Before current word
                         1. After current word
        '''
        w_id = word.getId()
        w_parent = word.node.getparent()
        w_node = word.node

        # The text will be converted to a loooong sentence 
        if text.strip() != '':

            if undo_stack is not None:
                cur_s = word.getParent()
                undo_stack.insert(0, ['INS_TEXT', cur_s, cur_s.node.__deepcopy__(False),
                                      cur_s.getParent().getElements().index(cur_s),
                                      cur_s.node.getparent().index(cur_s.node),
                                      undo_text, undo_pg, _(u'Desfazer inserção de texto.')])

            s_el = etree.Element('s', id='s_'+str(__builtin__.ids['s']))
            __builtin__.ids['s'] += 1
            s_el.text = text
            # Create sentence's word nodes
            Sentence(None, s_el)

            # Insert the new words before or after the current one
            pos = w_parent.index(word.node)
            if position == 1:
                pos += 1  # After
            for w in s_el.getchildren():
                w_parent.insert(pos, w)
                pos += 1

            # Redefine sentence words (and its children) IDs
            #self.updateSentenceWordsIDs(w_parent)
            # Update word lists based on new Sentence object
            old_list = word.getParent().getWordsList()
            word.getParent().rebuild(w_parent)
            self.updateWordLists(old_list, word.getParent().getWordsList())
    
            self.processPages()
    
        return self.getWordByRef(w_node.get('id'))

    def insertHeadFootText(self, page_nr, text, page_pos, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Insert text on page header or footer. Arguments:
            page_nr  --> Current page number
            text     --> Text to be inserted
            page_pos --> 0.Header   1.Footer
        '''
        if text.strip() != '':
            ed_types = []
            if __builtin__.cfg.get(u'Preferences', u'EditionTypes') != '':
                for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                    type, label = ed.split('|')
                    ed_types.append(type)
            ed_types.reverse()

            type = ['header', 'footer']
            if page_pos == 0:
                page_nr -= 1  # Header element is in the previous page break

            # Get or create a section element
            sce_node = None
            undo_obj = None
            if page_nr == 0 and page_pos == 0:
                # First page header
                parent_obj = self.elements_list[0]
                node = self.elements_list[0].node.getchildren()[0]
                if node.tag == 'sce' and node.get('t') == 'header':
                    sce_node = node
                    undo_obj = self.elements_list[0].elements_list[0]  # SectionEl
            elif page_nr == self.last_page and page_pos == 1:
                # Last page footer
                parent_obj = self.elements_list[-1]
                node = self.elements_list[-1].node.getchildren()[-1]
                if node.tag == 'sce' and node.get('t') == 'footer':
                    sce_node = node
                    undo_obj = self.elements_list[-1].elements_list[-1]  # SectionEl
            else:
                # Middle pages
                parent_obj = self.pages_list[page_nr-1][2]
                undo_obj = self.words_dict[self.pages_list[page_nr-1][1]]  # Word
                for node in self.pages_list[page_nr-1][2].node.getchildren():
                    if node.tag == 'sce' and node.get('t') == type[page_pos]:
                        sce_node = node
                        break
            if sce_node is None:
                sce_node = etree.Element('sce', id='sce_'+str(__builtin__.ids['sce']), t=type[page_pos])
                __builtin__.ids['sce'] += 1
                if page_pos == 0:
                    if parent_obj.node.tag == 'bk':
                        parent_obj.node.append(sce_node)
                    else:
                        parent_obj.node.insert(0, sce_node)
                else:
                    if parent_obj.node.tag == 'sc':
                        parent_obj.node.append(sce_node)
                    else:
                        parent_obj.node.insert(0, sce_node)

            if undo_stack is not None and undo_obj is not None:
                undo_stack.insert(0, ['HEAD_FOOT1', undo_obj, undo_obj.node.__deepcopy__(False),
                                      undo_obj.getParent().getElements().index(undo_obj),
                                      undo_obj.node.getparent().index(undo_obj.node),
                                      undo_text, undo_pg, _(u'Desfazer alteração de cabeçalho/rodapé.')])

            # Remove old text (if any), except for page number [DESABILITADO: 12/11/11, Pablo]
#            if len(sce_node.getchildren()) > 0:
#                for c in sce_node.getchildren():
#                    if c.tag == 'p': 
#                        sce_node.remove(c)

            # Generate text structure down to <o> and insert in the sce_node
            text = text.strip() 
            if len(text) > 0:
                # Generate text structure down to <o> and insert in the sce_node
                p_list = self.generateNodes(text)
                
                for p_el in p_list: 
                    if page_pos == 0:
                        sce_node.append(p_el)  # Header comes after page number (if any)
                    else:
                        if len(sce_node.getchildren()) > 0 and sce_node.getchildren()[-1].tag == 'te':
                            sce_node.insert(len(sce_node.getchildren()) - 1, p_el) # Footer comes before page number (if any)
                        else:
                            sce_node.append(p_el)

            # Rebuild parent_obj if a Break obj
            if parent_obj.node.tag == 'bk':
                # Update word lists based on new Sentence object
                old_list = parent_obj.getWordsList()
                parent_obj.rebuild(parent_obj.node)
                if len(old_list) > 0:
                    self.updateWordLists(old_list, parent_obj.getWordsList())
                else:
                    # Get the position of the word containing the break element in the words list
                    new_list = [self.words_dict[self.pages_list[page_nr-1][1]]]
                    new_list.extend(parent_obj.getWordsList())
                    self.updateWordLists([self.words_dict[self.pages_list[page_nr-1][1]]], new_list)
                    # Teste de rodapé para ecditar@cor_editar e ver o que rola . 
            else:
                # <sc> element (first page header or last page footer)
                sce_obj = SectionElement(parent_obj, sce_node)
                pos = ([0,-1])[page_pos]
                node = self.elements_list[pos].elements_list[pos].node
                old_list = []
                if node.tag == 'sce' and node.get('t') == type[page_pos]:
                    self.excludeFromObjectLists(self.elements_list[pos].elements_list[pos])
                    old_list = parent_obj.elements_list[pos].getWordsList()
                    parent_obj.remove(self.elements_list[pos].elements_list[pos])
                else:
                    if undo_stack is not None and undo_obj is None: #len(undo_stack) > 0 and undo_stack[0][0] == 'HEAD_FOOT1':
                        # It is a new SecEl that must be removed on undo
                        #undo_stack.pop(0)
                        undo_stack.insert(0, ['HEAD_FOOT2', parent_obj, sce_obj, undo_text, undo_pg,
                                              _(u'Desfazer alteração de cabeçalho/rodapé.')])
                if page_pos == 0:
                    parent_obj.elements_list.insert(0, sce_obj)
                    parent_obj.node.insert(0, sce_node)
                else:
                    parent_obj.elements_list.append(sce_obj)
                    parent_obj.node.append(sce_node)
                aux = eval('self.'+__builtin__.el_type_dict[sce_obj.__class__.__name__])
                aux[sce_obj.getId()] = sce_obj
                if not isinstance(sce_obj, Sentence): 
                    self.buildObjectLists(sce_obj.elements_list)
                if len(old_list) > 0:
                    self.updateWordLists(old_list, sce_obj.getWordsList())
                else:
                    # Insert at the begining of lists
                    new_list = sce_obj.getWordsList()
                    if page_pos == 0:
                        new_list.append(self.words_list[0])
                    else:
                        new_list.insert(0, self.words_list[-1])
                    self.updateWordLists([self.words_list[pos]], new_list)

            self.processPages()
            
            return True
        return False
    
    def generateNodes(self, text):
        '''
        Tokenize text and organize it in paragraphs and sentences.
        A lista of paragraphs nodes is then returned.
        '''
        p_list = []
        for p in contrib_nltk.tokenize.blankline(text):
            p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
            __builtin__.ids['p'] += 1
            p = p.strip()
            if len(p) > 0:
                if p[-1] not in ['.','!','?','\n']:
                    p = p + '\n'
                p = p + ' '
            for s in contrib_nltk.tokenize.regexp(p, r'(.+?)(\.\.)?[\.!?\n]+ '):
                if s.strip() != '':
                    s_el = etree.Element('s', id='s_'+str(__builtin__.ids['s']))
                    __builtin__.ids['s'] += 1
                    for tk in contrib_nltk.tokenize.regexp(s, r'[^\s]+'):
                        # Trata lista de edições [DESABILITADO, 12/11/11, Pablo]
#                        ed_list = [tk]
#                        if tk.find('@') >= 0:
#                            ed_list = tk.strip().split('@')
#                        t_list = [ed_list[0]]
#                        if tk.find('@') < 0:
                        # If there is no edition attached, the word may need to be splitted in two or more parts (eg, word+punctuation)
                        t_list = contrib_nltk.tokenize.regexp(tk, r'(\w+)?\$*(([\.,])?\d+)(([\.,])?\d+)?(([\.,])?\d+)?\$*|([\'~])?[\w\d]+([$\'~-])?([\w\d]+)?|(\.\.)?[^\w]')
#                        ed_list.pop(0)
                        for t in t_list:
                            w_el = etree.Element('w', id=str(__builtin__.ids['w']))
                            __builtin__.ids['w'] += 1
                            or_el = etree.SubElement(w_el, 'o') #, id='')
                            or_el.text = t.replace('_',' ') # <o> text with spaces comes with '_'
                            # Editions, if any (expected only if t_list has size 1) [DESABILITADO, 12/11/11, Pablo]
#                            for ed in ed_list:
#                                ed_type, ed_text = ed.split('_')
#                                if ed_type in ed_types and len(ed_text) > 0:
#                                    ed_el = etree.SubElement(w_el, 'e', t=ed_type)
#                                    ed_el.text = ed_text.replace('|',' ')
                            s_el.append(w_el)
                        #self.updateSentenceWordsIDs(s_el)
                    p_el.append(s_el)
                
                # Append to list
            p_list.append(p_el)
        return p_list
        
    
    def mergeElement(self, el_ref, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Merge the element with the previous of the same type.
        '''
        try:
            el = None
            prev_el = None
            if el_ref.find('s_') >= 0:
                el = self.getElementByRef(el_ref)
                if el is None:
                    return False, _(u"Elemento inexistente!")
                w_obj = el.getWordsList()[0]
                if w_obj.getParent().getParent().getParent().node.tag == 'sce' and\
                        w_obj ==\
                        w_obj.getParent().getParent().getParent().getWordsList()[0]:
                    # Merges from inside <sce> cannot access outside it
                    pass
                else:
                    for ii in range(self.words_id.index(w_obj.getId()) - 1,-1,-1):
                        prev_w = self.words_list[ii]
                        if w_obj.getParent().getParent().getParent().__class__.__name__ ==\
                                prev_w.getParent().getParent().getParent().__class__.__name__:
                            prev_el = prev_w.getParent()
                            break
            if el_ref.find('p_') >= 0:
                # Find Paragraph object
                el = self.getElementByRef(el_ref)
                parent = el.getParent()
                if parent.elements_list.index(el) == 0 and parent.getParent().elements_list.index(parent) > 0:
                    parent = parent.getParent().elements_list[parent.getParent().elements_list.index(parent) - 1]
                    ii = -1
                    while (ii*-1) <= len(parent.elements_list):
                        if isinstance(el, Paragraph):
                            prev_el = parent.elements_list[ii]
                            break
                        ii -= 1
                else:
                    for el_obj in parent.elements_list:
                        if el_obj.node.get('id') == el_ref:
                            break
                        if isinstance(el_obj, Paragraph):
                            prev_el = el_obj
            if el_ref.find('sc_') >= 0:
                for el in self.elements_list:
                    if el.node.get('id') == el_ref:
                        break
                    prev_el = el 

            if el.node.get('id') != el_ref:
                return False, _(u"Elemento inexistente!")
            
            # If found, merge them
            if prev_el is not None:
                # Set the information needed to undo the operation
                if undo_stack is not None:
                    if len(el.getParent().node.getchildren()) > 1:
                        undo_stack.insert(0,['MERGE', el, el.node.__deepcopy__(False),
                                             prev_el, prev_el.node.__deepcopy__(False),
                                             el.parent.elements_list.index(el),
                                             el.node.getparent().index(el.node),
                                             prev_el.parent.elements_list.index(prev_el),
                                             prev_el.node.getparent().index(prev_el.node), undo_text, undo_pg, _(u'Desfazer fusão.')])
                    else:
                        undo_stack.insert(0,['MERGE', el.getParent(), el.getParent().node.__deepcopy__(False),
                                             prev_el, prev_el.node.__deepcopy__(False),
                                             el.getParent().parent.elements_list.index(el.getParent()),
                                             el.getParent().node.getparent().index(el.getParent().node),
                                             prev_el.parent.elements_list.index(prev_el),
                                             prev_el.node.getparent().index(prev_el.node), undo_text, undo_pg, _(u'Desfazer fusão.')])

                if not isinstance(prev_el, Sentence):
                    prev_el.elements_list.extend(el.getElements())
                    for s in el.getElements():
                        s.parent = prev_el
                for child in el.getElements():
                    prev_el.node.append(child.node)
                el.parent.remove(el)
                if isinstance(prev_el, Sentence):
                    # Remove old sentence words from lists
                    self.updateWordLists(el.getWordsList(), [])
                    # Redefine sentence words (and its children) IDs
                    #self.updateSentenceWordsIDs(prev_el.node)
                    # Update words lists
                    old_list = prev_el.getWordsList()
                    prev_el.rebuild(prev_el.node)
                    self.updateWordLists(old_list, prev_el.getWordsList())
                # Update pages list
                self.processPages()
                
                return True, ''
            else:
                return False, _(u'Não há elemento anterior ao qual fundir.') 
        except:
            raise
        return False, ''

    def updateSentenceWordsIDs(self, s_node):
        '''
        Update IDs for <w> elements of the structure, after a
        change of the <s> ID.
        '''
        s_id = s_node.get('id')
        for ii in range(len(s_node.getchildren())):
            w_el = s_node.getchildren()[ii]
            if w_el.tag == 'w':
                old_id = w_el.get('id')
                new_id = str(__builtin__.ids['w']) #s_id+'#'+str(ii)
                __builtin__.ids['w'] += 1
                w_el.set('id', new_id)
#                for n_el in w_el.getchildren():
#                    n_el.set('id', n_el.get('id').replace(old_id, new_id))
        
    def breakSentence(self, word, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Break sentence after the word pointed too.
        '''
        if self.getNextWord(word) is not None and word.getParent() == self.getNextWord(word).getParent():
            cur_s = word.getParent()

            if undo_stack is not None:
                undo_stack.insert(0, ['BK_S', cur_s, cur_s.node.__deepcopy__(False),
                                      cur_s.getParent().getElements().index(cur_s),
                                      cur_s.node.getparent().index(cur_s.node), undo_text, undo_pg,
                                      _(u'Desfazer quebra de sentença.')])
                
            # Insert a new sentence node after the current one
            s_el = etree.Element('s', id='s_'+str(__builtin__.ids['s']))
            __builtin__.ids['s'] += 1
            # Transfer the words from (or after) the current
            #   to the new sentence
            pos = cur_s.node.index(word.node) + 1
            w_list = cur_s.node.getchildren()
            for kk in range(pos, len(w_list)):
                s_el.append(w_list[kk])
            # Redefine sentence words (and its children) IDs
            #self.updateSentenceWordsIDs(s_el)
            # Word lists 
            old_list = cur_s.getWordsList()
            cur_s.rebuild(cur_s.node)
            s_obj = Sentence(cur_s.getParent(), s_el)
            self.s_dict[s_obj.getId()] = s_obj
            new_list = cur_s.getWordsList()
            new_list.extend(s_obj.getWordsList())
            self.updateWordLists(old_list, new_list)
            # Insert new sentence in the paragraph
            pos = cur_s.node.getparent().getchildren().index(cur_s.node) 
            cur_s.node.getparent().insert(pos + 1, s_el)
            pos = cur_s.getParent().getElements().index(cur_s) 
            cur_s.getParent().elements_list.insert(pos + 1, s_obj)
            # Updates
            self.processPages()
            return self.words_dict[word.getId()]
        return None

    def getElements(self):
        '''
        Returns a copy of elements list.
        '''
        return self.elements_list[:]
    
    def getElementByRef(self, el_ref, parent=None):
        '''
        Returns the reference to element object (if found).
        '''
        prefix = el_ref[0:el_ref.rfind("_")]

        if el_ref in eval("self."+prefix+"_dict"):
             return eval("self."+prefix+"_dict[el_ref]")

#        if parent is None: parent = self
#
#        if prefix == 'te':
#            word = self.getWordByRef(el_ref+'#0')
#            return word.getParent()
#
#        if not isinstance(parent, Word):
#            # Section, Paragraph, Sentence ...
#            for el in parent.getElements():
#                if el.node.get('id') == el_ref:
#                    return el
#                el = self.getElementByRef(el_ref, el)
#                if el is not None: return el
#            # Break, SectionElement or TextElement  
#            for page in self.pages_list:
#                if page[2] is not None:
#                    if page[2].getId() == el_ref: return page[2] 
#                    el = page[2].getElementByRef(el_ref)
#                    if el is not None: return el
        return None
    
    def removeElementByRef(self, el_ref, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Remove the element from the document.
        '''
        try:
            tmp = self.getElementByRef(el_ref)

            if tmp is not None:
                aux = tmp.getParent()

                if undo_stack is not None:
                    # Obtain the previous immediate word object (relative to the element) (for undo)
                    w_obj = self.getPreviousWord(tmp.getWordsList()[0])
                    undo_stack.insert(0, ['EL-REMOVE', tmp, tmp.node.__deepcopy__(False),
                                          aux.getElements().index(tmp),
                                          aux.node.index(tmp.node), w_obj, aux.getId(),
                                          undo_text, undo_pg, _(u'Desfazer exclusão de elemento.')])

                    # Check whether the parent node became empty and delete it too
                    while len(aux.node.getchildren()) == 1 and not isinstance(aux, Break):
                        # Discard last undo, 'cause the parent will be put in there
                        undo_stack.pop(0)
                        # Obtain the previous immediate word object (relative to the element) (for undo)
                        w_obj = self.getPreviousWord(aux.getWordsList()[0])
                        undo_stack.insert(0, ['EL-REMOVE', aux, aux.node.__deepcopy__(False),
                                              aux.getParent().getElements().index(aux),
                                              aux.node.getparent().index(aux.node), w_obj, aux.getParent().getId(),
                                              undo_text, undo_pg, _(u'Desfazer exclusão de elemento.')])
                        tmp = aux
                        aux = aux.getParent()

                # Remove element
                aux.remove(tmp)

                # Remove from lists of each kind of element (sc, p, s, sce, te)
                self.excludeFromObjectLists(tmp)
                
                # Remove words of the elements, from words lists
                self.updateWordLists(tmp.getWordsList(), [])
                self.processPages()
                return True
        except:
            raise
        return False

    def breakSection(self, ref, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Breaks section immediately before the selected paragraph/sec_el.
        '''
        ref_obj = self.getElementByRef(ref)
        if ref_obj is not None and isinstance(ref_obj, (Paragraph,SectionElement)):
            if ref_obj.node.get('t') and ref_obj.node.get('t') in ['header','footer']:
                return False, _(u'Seção não pode ser finalizada no cabeçalho/rodapé.') 
            sec_obj = ref_obj.getParent()
            # XML node: creates a new section right after the current one
            sec_node = sec_obj.node
            text_node = sec_node.getparent()
            p_node_idx = sec_node.getchildren().index(ref_obj.node)
            if p_node_idx == 0 or (p_node_idx == 1 and sec_node.getchildren()[0].get('t') and sec_node.getchildren()[0].get('t') in ['header','footer']):
                # A section can not be empty
                return False, _(u'A seção atual não pode ficar vazia.')

            new_sec_node = etree.Element('sc', id='sc_'+str(__builtin__.ids['sc']))
            __builtin__.ids['sc'] += 1

            new_sec = Section(self, new_sec_node)
            self.sc_dict[new_sec.getId()] = new_sec
            self.elements_list.insert(self.elements_list.index(sec_obj) + 1, new_sec)
            text_node.insert(text_node.getchildren().index(sec_node) + 1, new_sec_node)

            # Objects: transfer objects to a new section
            p_idx = sec_obj.getElements().index(ref_obj)
            for el in sec_obj.getElements()[p_idx:]:
                new_sec.elements_list.append(el)
                new_sec_node.append(el.node)
                el.parent = new_sec
                sec_obj.elements_list.remove(el)

            if undo_stack is not None:
                undo_stack.insert(0, ['SEC_END', sec_obj, new_sec, undo_text, undo_pg, _(u'Desfazer quebra de seção.')])
            
            self.processPages()

            return True,''
        return False,''

    def breakText(self, ref, graphy, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Breaks text immediately before the selected paragraph/sec_el.
        '''
        ref_obj = self.getElementByRef(ref)
        if ref_obj is not None and isinstance(ref_obj, (Paragraph,SectionElement)):
            if ref_obj.node.get('t') and ref_obj.node.get('t') in ['header','footer']:
                return False, _(u'Texto não pode ser finalizado no cabeçalho/rodapé.') 

            sec_obj = ref_obj.getParent()
            sec_node = sec_obj.node
            sec_idx = self.elements_list.index(sec_obj)

            # Check the position of the break
            sec_node_idx = sec_node.getparent().getchildren().index(sec_node)
            p_node_idx = sec_node.getchildren().index(ref_obj.node)
            if sec_node_idx == 0 and (p_node_idx == 0 or (p_node_idx == 1 and sec_node.getchildren()[0].get('t') and sec_node.getchildren()[0].get('t') in ['header','footer'])):
                # A text cannot be empty
                return False, _(u'O texto atual não pode ficar vazio.')

            text_node = etree.Element('text', id='text_'+str(__builtin__.ids['text']))
            __builtin__.ids['text'] += 1
            new_text = Text(text_node)

            # Insert new text node int the <body> node
            self.node.getparent().insert(self.node.getparent().index(self.node) + 1, text_node)

            # Text being breaked in the middle of a section: split
            tmp_stack = None  # May hold undo information for section break
            if p_node_idx > 0:
                # XML node: creates a new section right after the current one
                tmp_stack = []
                self.breakSection(ref, tmp_stack)
            else:
                sec_idx -= 1
                
            # XML: transfer the rest of the sections to the new text
            for el in self.elements_list[sec_idx+1:]:
                new_text.elements_list.append(el)
                new_text.node.append(el.node)
                el.parent = new_text
                self.elements_list.remove(el)
                self.excludeFromObjectLists(el)

            # Insert text object in the texts list
            graphy.texts_list.insert(graphy.texts_list.index(self) + 1, new_text)

            if undo_stack is not None:
                undo_stack.insert(0, ['TEXT_END', self, new_text, tmp_stack, undo_text, undo_pg, _(u'Desfazer quebra de texto.')])
                
            # Update word lists to the current text
            self.words_dict = {}
            self.words_id = []
            self.words_list = []
            for el in self.getElements():
                for word in el.getWordsList():
                    self.words_id.append(word.getId())
                    self.words_list.append(word)
                    self.words_dict[word.getId()] = word
            self.processPages()
            self.updateDuplicates()

            # Update pages and word lists in the new text object
            new_text.buildObjectLists(new_text.getElements())
            for el in new_text.getElements():
                for word in el.getWordsList():
                    new_text.words_id.append(word.getId())
                    new_text.words_list.append(word)
                    new_text.words_dict[word.getId()] = word
            new_text.processPages()
            new_text.updateDuplicates()

            return True, ''
        return False, ''
            
    def importFromWordTagFormat(self, text, ed_level=['seg']):
        '''
        Compares each word/tag with a relevant word to see if they match and update the word object.
        '''
        # Prepares a list of relevant (to POS) word objects
        tmp_list = self.words_list[:]

        # List of words from tagged text
        text = re.sub(r"[\n\r]", ' ', text)
        text = re.sub(r" +", ' ', text)
        text = text.strip().strip('\n')
        w_list = text.split(' ')[:len(tmp_list)]
        w_list_size = len(w_list)

        # Update each word (if any mismatch is found, cancel the rest of the operation)
        while len(w_list) > 0 and len(tmp_list) > 0:
            if len(ed_level) == 0:
                w_str = tmp_list[0].getString().replace("/",'-')
            else:
                w_str = tmp_list[0].getString(ed_level).replace("/",'-')
#                w_str = tmp_list[0].getOriginalString().replace("/",'-')
#                for ed in ed_level:
#                    if tmp_list[0].isEdited(ed):
#                        w_str = tmp_list[0].getEditedString(ed).replace("/",'-')
#                        break
    
            word, tag = w_list[0].split('/')
            # Ignore words non-relevant to analysis
            if (not tmp_list[0].isRelevantToPOS() or\
                    w_str.replace("_","").strip() == ''):
               while len(tmp_list) > 0 and (not tmp_list[0].isRelevantToPOS() or\
                     w_str.replace("_","").strip() == ''):
                  tmp_list.pop(0)
               continue
            # Matching
            if len(tmp_list) > 0:
                w_parts = [w_str]
                if w_parts[0].find('_'):
                    # If word was segmented, process each part
                    w_parts = w_parts[0].split('_')
                ii = 0
                for w_text in w_parts:
                    if word != w_text:
                        return False, _(u'Arquivo informado não bate com o texto sendo editado. Importação cancelada.') + " (" + word + ":" + w_text + ")"
                    tmp_list[0].setPartOfSpeech(tag, ii)
                    w_list.pop(0)
                    if len(w_list) > 0:
                        word, tag = w_list[0].split('/')
                    ii += 1
                tmp_list.pop(0)
            
        return True, _(u"Importadas %d palavras.") % w_list_size
            
    def exportToWordTagFormat(self, doc_name, ed_level=["seg"], options=[], POS=True):
        '''
        Exports the XML document in the word/TAG format (as the
        one read by CorpusSearch).
        '''
        if doc_name == '':
            text = u''
        else:
            text = u'''|:| PLEASE SET CHARACTER ENCODING SYSTEM TO UTF-8
|:| Document ID: %s
|:| Title: %s
|:| Author: %s
|:| Last Saved: %s
|:| Encoding: UTF-8
|:| Version: Part-of-Speech tagged text
|:| Options: [edition level: '%s'] %s
|:| Generated by E-Dictor

'''%(doc_name, self.getTitle(), self.getAuthor(), time.strftime("%x"), ed_level[0], str(options))

        if 'PAGES' in options:
            text += "<P_1>/CODE\n\n"
            
        for section_obj in self.elements_list:
            text += section_obj.exportToWordTagFormat(ed_level,options,POS)
        return text
    
#    def exportToTextFormat(self, to_nlp=False, phonology=False):
#        '''
#        Exports the XML document to a text (TXT) format (optionally
#        suitable for natural language processing, ignoring
#        non-desired content).
#        '''
#        text = u''
#        for section_obj in self.elements_list:
#            text += section_obj.exportToText(to_nlp, phonology)
#        return text
    
    def exportText(self, doc_name, ed_level, file_type, options=[]):
        '''
        Exports the content of the XML according to the parameters.
        ed_level   --> (max) Level of edition.
        file_type  --> 1.TXT  2.HTML  3.HTML+FAC-SIMILE
        options    --> List of options:
                        "PHONOLOGICAL_TEXT" (when available, use phonological form)
                        "LINEBREAK_ON_SENTENCE" (break line at the end of each sentence)
                        "TOOLS_TEXT_ONLY" (only sections marked for automatic tools) 
                        "DO_BREAKLINES" (break lines on linebreak marks)
                        "PRINT_EL_TYPE" (print the 't' property for elements)
        '''
        content = None

        ignore_list = []
        if 'TOOLS_TEXT_ONLY' in options:
            # Build list of elements to be ignored
            if __builtin__.cfg.get(u'Preferences', u'ElementTypes') != '':
                for p in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                    while p.count('|') <= 2:
                        p += '|'
                    el, desc, pos, css = p.split('|')
                    if el == _(u'Seção') and pos == _(u'ignorar'):
                        ignore_list.append('sc:'+desc)
                    if el == _(u'Parágrafo') and pos == _(u'ignorar'):
                        ignore_list.append('p:'+desc)
                    if el == _(u'Sentença') and pos == _(u'ignorar'):
                        ignore_list.append('s:'+desc)
                    if el == _(u'Palavra') and pos == _(u'ignorar'):
                        ignore_list.append('w:'+desc)

        ed_type = [_(u'Texto original')]
        # Identifies the edition type
        if ed_level != ed_type[0]: 
            for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                type, label = ed.split('|')
                ed_type.append(type)
                if label == ed_level:
                    break
        ed_type.reverse()

        if file_type == 0:
            # TXT file
            # Header
            content = '''|:| [START HEADER]|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|
|:| PLEASE SET CHARACTER ENCODING SYSTEM TO UTF-8
|:| Document ID: %s
|:| Encoding: UTF-8
|:| Last Saved: %s
|:| Title: %s
|:| Author: %s
|:| Version: Simple Text [%s] %s
|:| Arquivo gerado pela ferramenta E-Dictor
|:| [END HEADER]|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|:|

'''%(doc_name, time.strftime("%x"), self.getTitle(), self.getAuthor(), ed_level, str(options))

            # First header of the text
            text_str = ''
            
            if 'TOOLS_TEXT_ONLY' not in options and self.elements_list[0].getPageHeader() is not None:
                text_str += self.elements_list[0].getPageHeader().exportToText(ed_type, options, ignore_list)

            # Process sections
            for section_obj in self.elements_list:
                text_str += section_obj.exportToText(ed_type, options, ignore_list)
            
            # Last footer of the text
            sep_bar = ''
            if 'TOOLS_TEXT_ONLY' not in options:
                # Last footer
                if self.elements_list[-1].getPageFooter() is not None:
                    text_str += self.elements_list[-1].getPageFooter().exportToText(ed_type, options, ignore_list)
                sep_bar = '================================================================================' 

            # Intermediate headers and footers (or only page nubmer marks)
            for page_nr in range(0, self.last_page):
                if self.pages_list[page_nr][2] is not None:
                    bk_text = self.pages_list[page_nr][2].exportToText('footer', ed_type, options) +\
                              '\n' + sep_bar + '\n'+\
                              self.pages_list[page_nr][2].exportToText('header', ed_type, options)
                else:
                    bk_text = sep_bar
                text_str = text_str.replace('[page: '+str(page_nr+1)+']', bk_text)
            
            text_str = re.sub(r'\n ', r'\n', text_str)
            text_str = re.sub(r'\n{3,}', r'\n\n', text_str)
            
            content += text_str
        elif file_type == 1:
            # HTML file
            # Header
            content = '''<html>
     <head>
        <title>:%s:Versão [%s]</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
     </head>
     <style>
     <!--
        BODY { font-family: Georgia, "Times New Roman", Times, serif; color: #000000; margin: 0px; padding: 0px; font-size: small; background: #dfdfdf;}
        a:link, a:visited, a:active, a:focus { color: #1268ca; text-decoration: none; }
        a:hover { text-decoration: overline; }
        H1{ font-size: 24px; color: #000000; margin: 20px 0px 10px; padding: 0px; font-weight: bold;}
        H2{ font-size: 18px; color: #000000; margin: 20px 0px 20px; padding: 0px; }
        H3{ font-size: 16px; color: #000000; margin: 20px 0px 10px; padding: 0px;}
        H4{ font-family: "Courier New", Courier, mono; font-size: 14px; font-weight: normal; color: #000000; margin: 0px; padding: 0px;}
        H5{ font-size: 14px; color: #666666; margin: 0px; padding: 0px;}
        H6{ font-size: 10px; color: #666666; margin: 0px; padding: 0px;}
        H7{ font-size: 12px; color: #666666; margin: 0px; padding: 0px;}
        span.el_type_color { color:#aaa; font-weight:normal; text-decoration: none; text-style: none;}
        span.el_type { color:#aaa; vertical-align:sub; font-size:7pt; font-weight:normal; text-decoration: none; text-style: none;}
        div.cap { float:left; font-size:28pt; display:block; margin-top:10px; padding-right:5px;}
        .small_text{ font-family: Verdana, Arial, Helvetica, sans-serif; color: #000000; font-size: 10px; }
        
        /* Comment elements */
        TABLE.comment { width: 95%%;}
        TD.commentAuthor { padding: 2px; width: 10%%; white-space: nowrap; background: #333333; color: #dfdfdf; text-align: center; border-bottom: 2px solid white; }
        TD.commentBody { padding: 3px; background: #ffffff; color: #336633; border-top: 1px solid #666666; border-bottom: 1px solid #666666; }
        SPAN.mark { background: #ffff07; padding: 1px; text-decoration: inherit; }
        SPAN.unmark { background: transparent; padding: 1px; text-decoration: inherit; }
        
        /* Layout Divs */
        .text_data {background:#507ba4; color:#fff; border: 2px solid #456c8a; padding:3px; font-size:8pt; font-family:Arial;}
        .catalog_file { width: 80%%; padding: 10px; position: relative; margin-top: 20px; border: 2px solid #666; background-color: #ffffff; text-align: left; }
        #content { width: 100%%; border-top: 1px solid #999999; }
        #text_content{ width: 80%%; border: 1px solid #000000; padding: 10px; margin-bottom: 25px; background-color:#FFFFFF; line-height: 18px; text-align: justify; }
        
        #text_content div.footer {border-top: 1px dotted #bfbfbf; padding: 0px; margin: 0px; margin-top:25px; font-size: 8pt;}
        #text_content div.header {border-bottom: 1px dotted #bfbfbf; padding: 0px; margin: 0px; margin-bottom:25px; font-size: 8pt;}

        /* User-defined (E-Dictor preferences) CSS */
        
'''%(doc_name, ed_level)

            # User defined CSS
            if __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').strip() != '':
                for el_def in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                    (el, type, pos, css) = el_def.split('|')
                    if len(css.strip()) > 0: 
                        if el == _(u"Seção"):
                            content += '        div.' + type + ' { ' + css + ' }\n'
                        elif el == _(u"Parágrafo"):
                            content += '        p.' + type + ' { ' + css + ' }\n'
                        elif el == _(u"Sentença"):
                            content += '        span.' + type + ' { ' + css + ' }\n'
                        elif el == _(u"Palavra"):
                            content += '        word.' + type + ' { ' + css + ' }\n'

            content +='''        
     -->
     </style>
     <body>
        <table id="content" width="80%%" cellpadding="0" cellspacing="0" align="center">
           <tr>
           <td align="center" valign="top">
                <br/>
                <div class="catalog_file">
                    <span class="small_text">|:| %s</span><br/>
                    <span class="small_text">|:| %s : "%s"</span><br/>
                    <span class="small_text">|:| Versão %s %s</span><br/>
                    <span class="small_text">|:| Arquivo gerado pela ferramenta <b>E-Dictor</b></span><br/>
                </div><!--end div catalog_file-->
                <br/>
                <br/>
                <span class="text_data">
                    "%s" (author: %s, %s) [ extensão: %s, %s palavras ]
                </span>
                <div id="text_content">
'''%(doc_name, self.getAuthor(), self.getTitle(), ed_level, str(options), 
     self.getTitle(), self.getAuthor(), self.getBorn(), self.getType(), str(len(self.words_list)))

            # First header of the text
            text_str = ''
            
            if 'TOOLS_TEXT_ONLY' not in options and self.elements_list[0].getPageHeader() is not None:
                text_str += self.elements_list[0].getPageHeader().exportToHtml(ed_type, options)

            # Process sections
            for section_obj in self.elements_list:
                text_str += section_obj.exportToHtml(ed_type, options, ignore_list)
            
            # Last footer of the text
            sep_bar = ''
            if 'TOOLS_TEXT_ONLY' not in options:
                # Last footer
                if self.elements_list[-1].getPageFooter() is not None:
                    text_str += self.elements_list[-1].getPageFooter().exportToHtml(ed_type, options)
                sep_bar = '<hr noshade="noshade" size="2" color="#aaaaaa"/>' 

            # Intermediate headers and footers (or only page nubmer marks)
            for page_nr in range(0, self.last_page):
                if self.pages_list[page_nr][2] is not None:
                    bk_text = self.pages_list[page_nr][2].exportToHtml('footer', ed_type, options) +\
                              sep_bar +\
                              self.pages_list[page_nr][2].exportToHtml('header', ed_type, options)
                else:
                    bk_text = sep_bar
                text_str = text_str.replace('[page: '+str(page_nr+1)+']<br/>', bk_text)
            
            content += text_str

            content += '''</div>
            </td>
         </tr>
      </table>
   </body>
</html>'''   

        else:
            # HTML file (with FAC-SIMILE area)
            # Header
            content = '''<html>
     <head>
        <title>:%s:Versão [%s]</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
     </head>
     <style>
     <!--
        BODY { font-family: Georgia, "Times New Roman", Times, serif; color: #000000; margin: 0px; padding: 0px; font-size: small; background: #dfdfdf;}
        a:link, a:visited, a:active, a:focus { color: #1268ca; text-decoration: none; }
        a:hover { text-decoration: overline; }
        H1{ font-size: 24px; color: #000000; margin: 20px 0px 10px; padding: 0px; font-weight: bold;}
        H2{ font-size: 18px; color: #000000; margin: 20px 0px 20px; padding: 0px; }
        H3{ font-size: 16px; color: #000000; margin: 20px 0px 10px; padding: 0px;}
        H4{ font-family: "Courier New", Courier, mono; font-size: 14px; font-weight: normal; color: #000000; margin: 0px; padding: 0px;}
        H5{ font-size: 14px; color: #666666; margin: 0px; padding: 0px;}
        H6{ font-size: 10px; color: #666666; margin: 0px; padding: 0px;}
        H7{ font-size: 12px; color: #666666; margin: 0px; padding: 0px;}
        span.el_type_color { color:#aaa; font-weight:normal; text-decoration: none; text-style: none;}
        span.el_type { color:#aaa; vertical-align:sub; font-size:7pt; font-weight:normal; text-decoration: none; text-style: none;}
        div.cap { float:left; font-size:28pt; display:block; margin-top:10px; padding-right:5px;}
        .small_text { font-family: Verdana, Arial, Helvetica, sans-serif; color: #000000; font-size: 10px; }
        hr.page_break {margin-top:0cm; margin-bottom:1cm; width:100%%; color:#aaa;}
        
        /* Comment elements */
        TABLE.comment { width: 95%%;}
        TD.commentAuthor { padding: 2px; width: 10%%; white-space: nowrap; background: #333333; color: #dfdfdf; text-align: center; border-bottom: 2px solid white; }
        TD.commentBody { padding: 3px; background: #ffffff; color: #336633; border-top: 1px solid #666666; border-bottom: 1px solid #666666; }
        SPAN.mark { background: #ffff07; padding: 1px; text-decoration: inherit; }
        SPAN.unmark { background: transparent; padding: 1px; text-decoration: inherit; }
        
        /* Layout Divs */
        .text_data {background:#507ba4; color:#fff; border: 2px solid #456c8a; padding:3px; font-size:8pt; font-family:Arial;}
        .catalog_info { width: 76%%; padding: .5cm; position: relative; margin-top: 20px; border: 2px solid #666; background-color: #ffffff; text-align: left; }
        #content { width: 100%%; border-top: 1px solid #999999; }
        #text_content{ width: 76%%; border: 0px solid #000000; padding: .5cm; margin-bottom: 25px; background-color:#FFFFFF; line-height: 18px; text-align: justify; }
        #text_content div.footer {border-top: 1px dotted #bfbfbf; padding: 0px; margin: 0px; margin-top:6pt; font-size: 8pt;}
        #text_content div.header {border-bottom: 1px dotted #bfbfbf; padding: 0px; margin: 0px; margin-bottom:6pt; font-size: 8pt;}
        
        /* Fac-simile */
        #text_content table {width: 100%%; border: 0px;}
        #text_content td.fac-simile {width: 300px; padding-bottom:6pt;}
        #text_content td.fac-simile img {width: 100%%; padding:3px; border: 1px solid #555; margin-bottom:9pt;}
        #text_content td.page {padding: 5px; text-align: justify; padding-left:1cm;}
        #text_content td.bar {height:2px; background:#bbb;}

        /* User-defined (E-Dictor preferences) CSS */
        
'''%(doc_name, ed_level)

            # User defined CSS
            for el_def in __builtin__.cfg.get(u'Preferences', u'ElementTypes').decode('utf-8').split(','):
                (el, type, pos, css) = el_def.split('|')
                if len(css.strip()) > 0: 
                    if el == _(u"Seção"):
                        content += '        div.' + type + ' { ' + css + ' }\n'
                    elif el == _(u"Parágrafo"):
                        content += '        p.' + type + ' { ' + css + ' }\n'
                    elif el == _(u"Sentença"):
                        content += '        span.' + type + ' { ' + css + ' }\n'
                    elif el == _(u"Palavra"):
                        content += '        word.' + type + ' { ' + css + ' }\n'

            content +='''        
     -->
     </style>
     <body>
        <table id="content" width="80%%" cellpadding="0" cellspacing="0" align="center">
           <tr>
           <td align="center" valign="top">
                <br/>
                <div class="catalog_info">
                    <span class="small_text">|:| %s</span><br/>
                    <span class="small_text">|:| %s : "%s"</span><br/>
                    <span class="small_text">|:| Versão %s %s</span><br/>
                    <span class="small_text">|:| Arquivo gerado pela ferramenta <b>E-Dictor</b></span><br/>
                </div><!--end div catalog_file-->
                <br/>
                <br/>
                <span class="text_data">
                    "%s" (author: %s, %s) [ extensão: %s, %s palavras ]
                </span>
                <div id="text_content">
                <table>
'''%(doc_name, self.getAuthor(), self.getTitle(), ed_level, str(options), 
     self.getTitle(), self.getAuthor(), self.getBorn(), self.getType(), str(len(self.words_list)))

            # First header of the text
            text_str = ''
            
            # First header of the text
            html_cells = '''
                <!-- Se necessário, inclua também o caminho (pasta/diretóri/url) do arquivo
                     (p.e., 'c:\\temp'). A numeração das páginas já está gerada (-1.jpg, -2.jpg,
                     ...). Caso necessário, substitua também a extensão '.JPG' para a que estiver
                     sendo utilizada (atentar para maiúsculas e minúsculas). -->

                <tr style="border-bottom: 3px double #aaa;">
                   <td valign="top" align="center" class="fac-simile">
                       <a href="%s-{p}.jpg" title="Ver ampliada">
                       <img src="%s-{p}.jpg" border="0"/></a></td>
                   <td class="page" valign="top">'''%(doc_name,doc_name)

            text_str += html_cells.replace('{p}','1')

            if 'TOOLS_TEXT_ONLY' not in options and self.elements_list[0].getPageHeader() is not None:
                text_str += self.elements_list[0].getPageHeader().exportToHtml(ed_type, options)
                            
            # Process sections
            for section_obj in self.elements_list:
                text_str += section_obj.exportToHtml(ed_type, options, ignore_list)
            
            # Last footer of the text
            if 'TOOLS_TEXT_ONLY' not in options:
                # Last footer
                if self.elements_list[-1].getPageFooter() is not None:
                    text_str += self.elements_list[-1].getPageFooter().exportToHtml(ed_type, options)

            sep_bar = '<hr class="page_break" noshade size="2"/>'
            
            # Intermediate headers and footers (or only page nubmer marks)
            for page_nr in range(0, self.last_page):
                if self.pages_list[page_nr][2] is not None:
                    bk_text = self.pages_list[page_nr][2].exportToHtml('footer', ed_type, options) + '</td></tr>' +\
                              '<tr><td colspan="2">' + sep_bar + '</td></tr>' +\
                              html_cells.replace('{p}', str(page_nr+2)) +\
                              '\n                ' + self.pages_list[page_nr][2].exportToHtml('header', ed_type, options)
                else:
                    bk_text = '</td></tr>\n' +\
                              html_cells.replace('{p}', str(page_nr+2)) + sep_bar
                # Primeiro, tenta no caso de haver link
                text_str = text_str.replace('<br/><br/>[page: '+str(page_nr+1)+']<br/><br/></a>', '</a>'+bk_text)
                # Depois, tenta a quebra sem link
                text_str = text_str.replace('<br/><br/>[page: '+str(page_nr+1)+']<br/><br/>', bk_text)
            
            content += text_str

            content += '''                </td></tr>
                </table>
                </div>
            </td>
         </tr>
      </table>
   </body>
</html>'''   

        return content

    def exportLex(self, doc_name, file_type, options=[]):
        '''
        Exports the list of edited tokens according to the parameters.
        file_type  --> CSV (comma separated values) or HTML 
                            use file_type.find("CSV") >= 0)
        options    --> List of options:
                        "ORDERED" (export in alphabetical order)
                        "GROUPED" (group items with same original form and 
                                   editions in a single line)
        '''
        content = None

        ed_types = []
        ed_labels = []
        for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
            type, label = ed.split('|')
            ed_types.append(type)
            ed_labels.append(label)

        if 'ORDERED' in options:
            # Build an ordered list of words
            keys = self.duplicates.keys()
            keys.sort(key=lambda s: (s.lower(), s))
            wid_list = []
            for k in keys:
                for w_id in self.duplicates[k]:
                    wid_list.append(w_id)
        else:
            wid_list = self.words_id[:]

        if file_type.find("CSV") >= 0:
            # TXT file: list of edited words and its editions separated by commas

            # Header
            content = '''|:| [%s]
|:| %s: "%s"
|:| Lista dos Itens Editados %s

'''%(doc_name, self.getAuthor(), self.getTitle(),str(options).replace('ORDERED',_('Ordenados')).replace('GROUPED',_('Agrupados')))

            content += 'Item'
            for label in ed_labels:
                content += ',' + label
            content += '\n'

            # Items
            if 'GROUPED' in options:
                # This option is available only with 'ORDERED'
                last_tk = ''
                for w_id in wid_list:
                    w_obj = self.words_dict[w_id]
                    if w_obj.isEdited():
                        if last_tk != w_obj.getOriginalString():
                            last_tk = w_obj.getOriginalString()
                            content += last_tk
                            last_eds = []
                        ed_line = ''
                        for type in ed_types:
                            ed_line += ',' + w_obj.getEditedString(type)
                        if ed_line not in last_eds:
                            last_eds.append(ed_line)
                            content += ed_line
                            content += '\n'
            else:
                for w_id in wid_list:
                    w_obj = self.words_dict[w_id]
                    if w_obj.isEdited():
                        content += w_obj.getOriginalString()
                        for type in ed_types:
                            content += ',' + w_obj.getEditedString(type)
                        content += '\n'
        else:
            # HTML file

            # Header
            content = '''<html>
   <head>
      <title>%s:Léxico das Edições</title>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
   </head>
   <style>
   <!--
    body{ font-family: Georgia, "Times New Roman", Times, serif; color: #000000; margin: 10px; padding: 0px; font-size: small; background-color:#eeeedd;}
    a:link{ color: #666666; text-decoration: none;}
    a:visited{color: #999999;text-decoration: none;}
    a:hover{ color: #333333; text-decoration: underline;}
    h1{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 24px; color: #000000; margin: 20px 0px 10px; padding: 0px; font-weight: bold;}
    h2{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 18px; color: #000000; margin: 20px 0px 20px; padding: 0px;}
    h3{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 16px; color: #000000; margin: 20px 0px 10px; padding: 0px; }
    h4{ font-family: "Courier New", Courier, mono; font-size: 14px; font-weight: normal; color: #000000; margin: 0px;  padding: 0px; }
    h5{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 14px; color: #999999; margin: 0px; padding: 0px;}
    h6{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 10px; color: #666666; margin: 0px; padding: 0px;}
    h7{ font-family: Georgia, "Times New Roman", Times, serif; font-size: 12px; color: #999999; margin: 0px; padding: 0px;}
    
    /***********************************************/
    /* Layout Divs                                 */
    /***********************************************/
    #top { margin: 0px 0px 0px 20px; padding: 0px; position: static;}
    #navBar{ padding: 2px; overflow: auto; float: right; width: 100%%; position: relative; visibility: inherit; margin-bottom: 10px; margin-left: 2px; border-top: #000000; font-family: "Courier New", Courier, mono; color: #333333; text-align: right;}
    .catalog_file { text-align: left; padding: 10px; position: relative; background-color: #ffffff; margin: 0 auto; border-top: 1px solid #000000; border-right: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000;}
    #content{width: 100%%;}
    #masthead{float: left; padding-right: 30px; padding-left: 30px; margin-left: 50px; margin-top: 20px; margin-bottom: 10px; border: 1px solid #000000; text-align: justify; width: 60%%; font-family: "Courier New", Courier, mono; font-size: 10px; color: #333333; background-color:#FFFFFF;}
    #text_content{ background-color:#FFFFFF; line-height: 18px; text-align: justify; margin: 0 auto; margin-top:10px; padding: 10px; border: 1px solid #000000;}
    #catalog{ float: left; padding: 5px 10px;border: 1px solid #000000; margin-left: 20px; margin-bottom: 20px; font-family: "Courier New", Courier, mono; font-size: small; font-weight: normal; color: #666633; margin-top: 20px; background-color: #FFFFFF; width: 85%%;}
    
    /*********** #navBar link styles ***********/
    #navBar a:link { font-family: "Courier New", Courier, mono; font-size: 12px; font-weight: normal;color: #333333; letter-spacing: 0.1em; text-decoration: none;}
    #navBar a:hover{font-family: "Courier New", Courier, mono; font-size: 12px; font-weight: normal;letter-spacing: 0.1em; color: #990000; text-decoration: underline; width: auto;}
    #navBar a:visited { font-family: "Courier New", Courier, mono; font-size: 12px; font-weight: normal; color: #333333;letter-spacing: 0.1em; text-decoration: none;}
    
    /************* #catalog styles **************/
    
    #catalog a { font-size: 90%%; padding: 1px 4px 4px; font-family: Georgia, "Times New Roman", Times, serif; font-weight: normal; color: #999966; letter-spacing: 0.1em;}
    #catalog a:hover{ color: #006699; text-decoration: none; background-color: #ffffff; border: thin solid #cccccc;}
    #catalog_table{ padding: 0px 0px 5px; color: #333333; font-size: small; background-color: #fffff; float: left; width: 80%%; border: 1px solid #FFFFFF; font-family: "Courier New", Courier, mono;}
    .catalog_text { float: left; padding: 10px 10px 0px 0px; font-family: "Courier New", Courier, mono; font-size: small; color: #333333;}
    #catalog_source { padding: 0px 0px 5px; background-color: #FFFFFF; float: left; border: 1px solid #000000; margin-left: 20px;margin-bottom: 20px; width: 700px;}
    
    /*************** #pageName styles **************/
    
    #Title{ margin: 0px; padding: 0px 0px 0px 10px;}
    
    /************** .content styles ***************/
    
    .page{ background-color: #999999; width: 90%%;}
    .small_text{ font-family: Verdana, Arial, Helvetica, sans-serif; color: #000000; font-size: 10px;}
    .content_text{ padding: 0px 0px 10px 10px; font-family: Georgia, "Times New Roman", Times, serif; color: #000000; font-size: 10px;}
    .content_text h3{ padding: 30px 0px 5px 0px; text-align: center;}
    .content_text img{ float: left; padding: 10px 10px 0px 0px;}
    .lex_text { font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12px; color: #000000; text-align: center;}
    .textsans {    font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10px; color: #000000;}
    -->
    </style>
   <body>
      <div class="catalog_file">
         <span class="small_text">|:| [%s]</span><br/>
         <span class="small_text">|:| %s: "%s"</span><br/>
         <span class="small_text">|:| <b>Lista dos Itens Editados</b> %s</span><br/>
      </div>
      <div id="text_content">
         <table width="100%%" bgcolor="#ffffff" cellpadding="0" cellspacing="1">
            <tr>
               <td align="center" style="border-bottom: 2px solid #000;"><b>Item</b></td>
'''%(doc_name,doc_name,self.getAuthor(),self.getTitle(),str(options).replace('ORDERED',_('Ordenados')).replace('GROUPED',_('Agrupados')))

            # Completion of table columns headers
            color = ['#dfdfdf','#efefef']
            for label in ed_labels:
                content += '<td align="center" bgcolor="' + color[0] + \
                           '" style="border-bottom: 2px solid #000;"><b>' + label + \
                           '</b></td>'
                color.reverse() # Alternate colors among columns
            content += "</tr>"
            
            # Table items
            if 'GROUPED' in options:
                # This option is available only with 'ORDERED'
                last_tk = ''
                for w_id in wid_list:
                    w_obj = self.words_dict[w_id]
                    if w_obj.isEdited():
                        if last_tk != w_obj.getOriginalString():
                            last_tk = w_obj.getOriginalString()
                            content += '<tr><td style="border-top:1px solid black;" bgcolor="#ffffff">' + last_tk + '</td>' # ' (qt0)</td>'
                            last_eds = []
                        ed_line = ''
                        color = ['#dfdfdf','#efefef']
                        for type in ed_types:
                            ed_line += '<td align="center" bgcolor="' + color[0] + '">' + w_obj.getEditedString(type) + '</td>'
                            color.reverse()
                        if ed_line not in last_eds:
                            if len(last_eds) > 0:
                                content += '<tr><td bgcolor="#ffffff"></td>'
                            last_eds.append(ed_line)
                            content += ed_line
                            content += '</tr>'
            else:
                for w_id in wid_list:
                    w_obj = self.words_dict[w_id]
                    if w_obj.isEdited():
                        content += '<tr><td bgcolor="#ffffff">' + w_obj.getOriginalString() + '</td>'
                        color = ['#dfdfdf','#efefef']
                        for type in ed_types:
                            content += '<td align="center" bgcolor="' + color[0] + '">' + w_obj.getEditedString(type) + '</td>'
                            color.reverse() # Alternate colors among columns
                        content += '</tr>'

            # Footer
            content += '''
         </table>
      </div>
   </body>
</html>
'''
        return content

class Graphy():
    '''
    This class wraps the XML document and provides general operations
    over its content.
    '''
    def __init__(self):
        # Set app language
        intl.setLanguage()
        self.file_name = None
        self.mapping = None
        self.texts_list = []
        self.modified = False
        self.stylesheet = 'teste.xsl'
        # Initial ID counters
        __builtin__.ids = {'text':1,\
                           'sc':1,\
                           'sce':1,\
                           'te':1,\
                           'p':1,\
                           's':1,\
                           'w':1,\
                           'comment':1,\
                           'bk':1}

    def SaveXMLFile(self, file_name, modf=False):
        '''
        Save the XML tree in a document specified by the user.
        '''
        try:
            # Update 'words' property for all texts and the global word count (in metadata)
            total_words = 0
            for text_obj in self.getTexts():
                text_obj.node.set('words', str(len(text_obj.getWordsList())))
                total_words += len(text_obj.getWordsList())
            try:
                # Internal metadata
                mdata = self.getMetadata()
                if not 'edictor_internal' in mdata:
                    mdata['edictor_internal'] = []
                    mdata['edictor_internal'].append(('Document Name','')) 
                    mdata['edictor_internal'].append(('XML generated by','E-Dictor-v'+str(__builtin__.version)))
                    mdata['edictor_internal'].append(('Last Saved Date',time.strftime('%d.%m.%Y', time.localtime())))
                    mdata['edictor_internal'].append(('Word Count',str(total_words)))
                else:
                    for mfield in mdata['edictor_internal']:
                        if mfield[0] == "Word Count":
                            mfield[1] = str(total_words)
                        if mfield[0] == 'XML generated by':
                            mfield[1] = 'E-Dictor-v'+str(__builtin__.version)
                        if mfield[0] == "Last Saved Date":
                            mfield[1] = time.strftime('%d.%m.%Y', time.localtime())
                self.setMetadata(mdata)
            except:
                pass
            self.removeEmptyProperties(self.etree.getroot())

            # Add Processing Instructions to the XML file [WAITING FOR A 'delete()' FUNCTION IN LXML : ppff, 26/11/11]
            #if self.etree.getroot().getprevious() is None: 
            #    pi = etree.ProcessingInstruction('xml-stylesheet', 'href="' + self.stylesheet + '" type="text/xsl"')
            #    self.etree.getroot().addprevious(pi)
            
            self.etree.write(file_name.encode('utf-8'), encoding='utf-8', pretty_print=True, xml_declaration=True)
            self.modified = modf
        except:
            raise
        
    def removeEmptyProperties(self, node):
        '''
        Clear empty properties from de XML nodes.
        '''
        for k, v in node.attrib.iteritems():
            if len(v.strip()) == 0:
                del node.attrib[k]
        # Recursive call
        for child in node.getchildren():
            self.removeEmptyProperties(child)
        
    def OpenXMLFile(self, file_name):
        '''
        Open the XML file, builds the parse tree and generates
        the object structure for accessing the the content of the document.
        '''
        try:
            #* attribute_defaults - read the DTD (if referenced by the document) and add the default attributes from it
            #* dtd_validation - validate while parsing (if a DTD was referenced)
            #* load_dtd - load and parse the DTD while parsing (no validation is performed)
            #* no_network - prevent network access when looking up external documents
            #* ns_clean - try to clean up redundant namespace declarations
            #* recover - try hard to parse through broken XML
            #* remove_blank_text - discard blank text nodes between tags
            #* remove_comments - discard comments
            #* compact - use compact storage for short text content (on by default)
            parser = etree.XMLParser(attribute_defaults=True, dtd_validation=False, remove_blank_text=True) #, remove_pis=True)
            self.etree = etree.parse(file_name.encode('utf-8'), parser)
            self._validateXML()
            self._generateIDs(self.etree.getroot())
#            self.teste(self.etree.getroot())
            self._build()
            self.file_name = file_name
            return True
        except XMLValidationError:
            raise BaseException, _(u"Erro: arquivo XML inválido: ") + (str(sys.exc_info()[0]) + str(sys.exc_info()[1])).encode('utf-8')
        return False

    def teste(self, node):
        for c in node.getchildren():
            if c.tag in ['m','f']: print c.attrib, c.text
            self.teste(c)
            
    def _validateXML(self):
        '''
        Check if there is at least one <text> element and other
        issues.
        '''
        try:
            for el_text in self.etree.getroot().getiterator('text'):
                mapping = el_text.attrib.get('mapping')
                if mapping is not None:
                    if mapping == 'logic':
                        self.mapping = mapping
                    else:
                        raise XMLValidationError, _(u"Mapeamento do tipo '%s' não suportado.")%mapping.encode('utf-8')
        except:
            raise

    def _generateIDs(self, node):
        '''
        Regenerate the IDs of all elements in the document tree.
        '''
        # Remove empty nodes (that shouldn't be empty)
        if len(node.getchildren()) == 0 and node.text == u'' and\
                node.tag not in ['bk','meta','n','v','fac-simile','o','e','f','m']:
            node.getparent().remove(node)
        # Process each child node
        for el in node.getchildren():
            # Set the ID
            if el.tag not in ['head','metadata','meta','n','v','body']:
                id = None
                if el.tag in __builtin__.ids.keys():
                    if el.tag != 'w':
                        id = el.tag.lower() + '_' + str(__builtin__.ids[el.tag])
                    else:
                        id = str(__builtin__.ids[el.tag])
                    __builtin__.ids[el.tag] += 1
                else:
                    if False: #el.tag == 'w':
                        id = el.getparent().get('id')+'#'+str(node.getchildren().index(el))
                    elif el.tag in ['o','m','f']:
                        pass # id = el.getparent().get('id')+'#'+el.tag
                    elif el.tag == 'e':
                        pass # id = el.getparent().get('id')+'#'+el.get('t')
                    elif isinstance(el.tag, (str)):
                        if el.tag not in __builtin__.ids.keys():
                            __builtin__.ids[el.tag] = 0
                        id = el.tag + '_' + str(__builtin__.ids[el.tag])
                    else: continue
                if id is not None:
                    el.set('id', id)
                elif 'id' in el.attrib:
                    del el.attrib['id']
            # Process node children (recursively)
            self._generateIDs(el)

    def _build(self):
        '''
        Builds the object structure of the document.
        '''
        # Process text elements
        for text in self.etree.getroot().getiterator('text'):
            text_obj = Text(text)
            self.texts_list.append(text_obj)
            if len(text_obj.getPagesList()) == 1 and len(text_obj.getWordsList()) > 700:
                # Insert "dumb" page breaks if the text is too long (this avoids a heavy load on the application)
                for ii in range(700, len(text_obj.getWordsList()), 700):
                    text_obj.getWordsList()[ii].insertBreak(text_obj.getWordsList()[ii].getString()+'|', 'p', [], '')
                text_obj.processPages()
        
        if len(self.texts_list) == 0:
            raise XMLValidationError, _(u"Nenhum elemento 'text' encontrado.")

    def newTextFromNode(self, node, pos):
        '''
        Builds the object structure for the text node specified.
        '''
        # Process text elements
        text_obj = Text(node)
        self.texts_list.append(text_obj)
        for text in self.etree.getroot().getiterator('text'):
            t_node = text
            break
        t_node.getparent().insert(pos, node)
        if len(text_obj.getPagesList()) == 1 and len(text_obj.getWordsList()) > 700:
            # Insert "dumb" page breaks if the text is too long (this avoids a heavy load on the application)
            for ii in range(700, len(text_obj.getWordsList()), 700):
                text_obj.getWordsList()[ii].insertBreak(text_obj.getWordsList()[ii].getString()+'|', 'p', [], '')
            text_obj.processPages()
            
    def createFromText(self, text, prefix='id'):
        '''
        Create a new XML tree structure based on raw text.
        Any existing data will be lost.
        '''
    
        if re.sub('@pag@','',re.sub('@>(.*?)<@','',text)).strip() == '':
            return False, _(u"Não há texto a processar.")
        
        xml_str = '''<!-- Para atribuir uma folha de estilos (XSLT) basta informar o nome da 
     folha no campo 'href' na linha abaixo --> 
<?xml-stylesheet href="" type="text/xsl"?>
<document>
    <head id="%s">
        <metadata generation="edictor_internal">
            <meta>
                <n>Document Name</n>
                <v>%s</v>
            </meta>
            <meta>
                <n>XML generated by</n>
                <v>%s</v>
            </meta>
            <meta>
                <n>Last Saved Date</n>
                <v>%s</v>
            </meta>
            <meta>
                <n>Word Count</n>
                <v></v>
            </meta>
        </metadata>
    </head>
</document>
'''%(str(prefix), str(prefix), 'EDictor-v'+str(__builtin__.version),
         time.strftime('%d.%m.%Y', time.localtime()))
        parser = etree.XMLParser(attribute_defaults=True, dtd_validation=False, remove_blank_text=True)
        tree = etree.parse(StringIO(xml_str), parser)
        root = tree.getroot()
        body = etree.SubElement(root, 'body')
        text_el = etree.SubElement(body, 'text', id='text_'+str(__builtin__.ids['text']), t='full', words='', year='', title='', author='', born='')
        __builtin__.ids['text'] += 1
        sec_el = etree.SubElement(text_el, 'sc', id='sc_'+str(__builtin__.ids['sc']), t='')
        __builtin__.ids['sc'] += 1

        if text.endswith('@pag@'): 
            text = text[:len(text) - 5] 

        # Pre-process comments
        comm_list = []
        for comm in contrib_nltk.tokenize.regexp(text, r'@>comm:(.*?)<@'):
            comm_list.append(comm)
        comm_count = 0
        for comm in comm_list:
            text = text.replace(comm, '@'+str(comm_count)+'@')
            comm_count += 1

#        # Break paragraphs at blanklines
#        for p in contrib_nltk.tokenize.blankline(text):
#            p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
#
#            # Lines starting by a lowercase letter will not be treated as new sentences 
#            #m = re.findall(r"\n( *)(\w)", p, re.UNICODE)
#            #for ii in range(len(m)):
#            #    if m[ii][1] == m[ii][1].lower():
#            #        p = p.replace("\n"+m[ii][0]+m[ii][1], u" " + m[ii][1])
#
#            # Break sentences at ., ? and ! markers
#            p = p.strip()
#            if not p.startswith('|:|'):
#                # Quebras de linha serão consideradas como marcas explícitas de quebras
#                p = p.replace('\n',' @ln@ ')
#                # Remove marcações de quebra duplicadas
#                p = re.sub(r'( *@(ln|pag|col)@ *)+', r' @\2@ ', p, re.IGNORECASE | re.UNICODE)
#                # Tratamento de contrações aqui (se houver)
#                p = self.codifySpecialWords(p)
#
#                # Insere uma marca temporária de fim de sentença, caso não haja nenhuma convencional
#                if len(p) > 0:
#                    if p[-1] not in ['.','!','?','\n']:
#                        p = p + ' PONFP'
#                    p = p + ' '
#                
#                for s in contrib_nltk.tokenize.regexp(p, r'((.+?)[\.!?]+( (@ln@|@pag@|@col@) )?|(.+?)PONFP)'):
#                    if s.strip() != '':
#                        s = s.replace('PONFP','')
#                        s_el = etree.SubElement(p_el, 's', id='s_'+str(__builtin__.ids['s']))
#                        __builtin__.ids['s'] += 1
#                        #s_el.text = s
#                        # Comments: each one enters as a property of node s_el
#                        comm = re.findall(r"@[0-9]+@", s)
#                        for ii in range(len(comm)):
#                            s_el.set('comm'+comm[ii].replace('@',''), comm_list[int(comm[ii].replace('@',''))])
#
#                        # Trying a more "inteligent" (and maybe dangerous) tokenization...
#                        new_el = None
#                        or_el = None
#                        for tk in contrib_nltk.tokenize.regexp(s, r'[^\s]+'):
#                            for t in contrib_nltk.tokenize.regexp(tk, r'@[0-9]+@|@pag@|@ln@|@col@|(\w+)?\$*(([\.,])?\d+)(([\.,])?\d+)?(([\.,])?\d+)?\$*|([\'~])?[\w\d]+([$\'~-])?([\w\d]+)?|(\.\.)?[^\w]'):
#                                if len(t) <= 2 or (t[0] != '@' and t[-1] != '@'):
#                                    loc = str(__builtin__.ids['w']) #self.id + '#' + str(i)
#                                    __builtin__.ids['w'] += 1
#                                    new_el = s_el.makeelement('w', id=loc)
#                                    or_el  = etree.SubElement(new_el, 'o') #, id=loc+'#o')
#                                    or_el.text = t.strip()
#                                    s_el.append(new_el)
#                                elif new_el is not None and len(t) > 1 and t[0] == '@' and t[-1] == '@':
#                                    if t == "@pag@":
#                                        if or_el.find('bk') is None:
#                                            break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='p')
#                                            __builtin__.ids['bk'] += 1
#                                    elif t == "@ln@":
#                                        if or_el.find('bk') is None:
#                                            break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='l')
#                                            __builtin__.ids['bk'] += 1
#                                    elif t == "@col@":
#                                        if or_el.find('bk') is None:
#                                            break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='c')
#                                            __builtin__.ids['bk'] += 1
#                                    else:
#                                        (ab,author,date,title,txt,fc) = s_el.get('comm'+t.replace('@','')).split(':')
#                                        comm_node = etree.SubElement(new_el, 'comment')
#                                        comm_obj = Comment(None, comm_node)
#                                        comm_obj.setAuthor(author)
#                                        comm_obj.setDate(date)
#                                        comm_obj.setTitle(title)
#                                        comm_obj.setText(txt)
#                                        s_el.set('comm'+t.replace('@',''),'')
#
#            # Include paragraph only if it has some content
#            if len(p_el.getchildren()) > 0:
#                sec_el.append(p_el)
#                __builtin__.ids['p'] += 1

        self.buildTextNodes(text, sec_el)
                     
        self.etree = tree
        self._build()
        self.modified = True

        return True, ''
    
    def buildTextNodes(self, text, sec_node):
        expr = [r'[\(\[\{\'"]',  # Abertura de parênteses, aspas, etc.
                r'[\)\]\}]',  # Fechamento de parênteses
                r'^[¿¡]',  # Pontuações no início da sentença (espanhol)
                r'[\.!?;:,]+$',  # Pontuações ao final das palavras
                r'.*[^\.!?;:,\)\]\}\'"]']  # Palavras (alfanumérico)
        
        # Anexa a lista de tokens especiais a tratar (contrações, etc.)
        if __builtin__.cfg.get(u'Preferences', u'XML_list').strip() != '':
            xml_list = __builtin__.cfg.get(u'Preferences', u'XML_list').split('|')
            for it in xml_list:
                # Cada item é tranformado numa expressão regular
                #expr.insert(0, re.escape(it))
                expr.insert(0, it)

        # Parágrafos são definidos pelo salto de uma linha em branco
        for p in contrib_nltk.tokenize.blankline(text):
            # Se não houver texto, ignora
            p = p.strip()
            if p == '': continue

            # Ignora sentenças que iniciam por "|:|" (comentários)
            if p.startswith('|:|'): continue

            # Nó do parágrafo
            p_el = etree.Element('p', id='p_'+str(__builtin__.ids['p']))
            __builtin__.ids['p'] += 1

            # Lines starting by a lowercase letter will not be treated as new sentences 
            #m = re.findall(r"\n( *)(\w)", p, re.UNICODE)
            #for ii in range(len(m)):
            #    if m[ii][1] == m[ii][1].lower():
            #        p = p.replace("\n"+m[ii][0]+m[ii][1], u" " + m[ii][1])

            # Quebras de linha serão consideradas como marcas explícitas de quebras
            p = p.replace('\n',' @ln@ ')
            # Remove marcações de quebra duplicadas (mesmo que de tipos distintos)
            p = re.sub(r'( *@(ln|pag|col)@ *)+', r' @\2@ ', p, re.IGNORECASE | re.UNICODE)
            # Separa marcações de quebra do item que as precede
            p = re.sub(r'([^ ])@(ln|pag|col)@', r'\1 @\2@ ', p, re.IGNORECASE | re.UNICODE)

            p_rev = ''
            
            # Passo 1: tokeniza primeiramente por espaço em branco
            for pre_tk in contrib_nltk.tokenize.regexp(p, r'[^\s]+'):
                # Passo 2: retokeniza os tokens obtidos com base na lista de expressões
                for punc_tk in contrib_nltk.tokenize.regexp(pre_tk, '|'.join(expr)):
                    p_rev += punc_tk + ' '
                    
            # Passo 3: agora, que identificamos mais confiavelmente as pontuações de
            #          fim de sentença, fazemos a separação das sentenças
            #for s in contrib_nltk.tokenize.regexp(p_rev, r'(.+?)( ([\.!?]+ (@(ln|pag|col)@)?)? |$)'):
            for s in contrib_nltk.tokenize.regexp(p_rev, r'(.+?) [\.!?] *(@(ln|pag|col)@)? *|(.+?) $'):
                # Ignora sentença em branco
                if s.strip() == '': continue

                # Nó da sentença
                s_el = etree.SubElement(p_el, 's', id='s_'+str(__builtin__.ids['s']))
                __builtin__.ids['s'] += 1

                # Comments: each one enters as a property of node s_el
                comm = re.findall(r"@[0-9]+@", s)
                for ii in range(len(comm)):
                    s_el.set('comm'+comm[ii].replace('@',''), comm_list[int(comm[ii].replace('@',''))])
                
                # Trying a more "inteligent" (and maybe dangerous) tokenization...
                new_el = None
                or_el = None
                for t in contrib_nltk.tokenize.regexp(s, r'[^\s]+'):
                    if len(t) <= 2 or (t[0] != '@' and t[-1] != '@'):
                        loc = str(__builtin__.ids['w']) #self.id + '#' + str(i)
                        __builtin__.ids['w'] += 1
                        new_el = s_el.makeelement('w', id=loc)
                        or_el  = etree.SubElement(new_el, 'o') #, id=loc+'#o')
                        or_el.text = t.strip()
                        s_el.append(new_el)
                    elif new_el is not None and len(t) > 1 and t[0] == '@' and t[-1] == '@':
                        if t == "@pag@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='p')
                                __builtin__.ids['bk'] += 1
                        elif t == "@ln@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='l')
                                __builtin__.ids['bk'] += 1
                        elif t == "@col@":
                            if or_el.find('bk') is None:
                                break_el = etree.SubElement(or_el, 'bk', id='bk_'+str(__builtin__.ids['bk']), t='c')
                                __builtin__.ids['bk'] += 1
                        else:
                            (ab,author,date,title,txt,fc) = s_el.get('comm'+t.replace('@','')).split(':')
                            comm_node = etree.SubElement(new_el, 'comment')
                            comm_obj = Comment(None, comm_node)
                            comm_obj.setAuthor(author)
                            comm_obj.setDate(date)
                            comm_obj.setTitle(title)
                            comm_obj.setText(txt)
                            s_el.set('comm'+t.replace('@',''),'')

            # Inclui parágrafo na seção
            if len(p_el.getchildren()) > 0:
                sec_node.append(p_el)
            
    
    def codifySpecialWords(self, str):
        '''
        Codifica sequências especiais de texto, como contrações, valores, etc.
        '''
        return str

    def isModified(self):
        return self.modified

    def setPrefix(self, prefix='id'):
        '''
        Changes de 'id' of the XML document based on the file name choosen by
        the user. Returns True if it succeeds.
        '''
        try:
            # Internal metadata
            mdata = self.getMetadata()
            if not 'edictor_internal' in mdata:
                mdata['edictor_internal'] = []
                mdata['edictor_internal'].append(('Document Name',prefix)) 
                mdata['edictor_internal'].append(('XML generated by','E-Dictor-v'+str(__builtin__.version)))
                mdata['edictor_internal'].append(('Last Saved Date',time.strftime('%d.%m.%Y', time.localtime())))
                mdata['edictor_internal'].append(('Word Count',''))
            else:
                for mfield in mdata['edictor_internal']:
                    if mfield[0] == "Document Name":
                        mfield[1] = prefix
                        break
            self.setMetadata(mdata)
            head = self.etree.xpath('//head') # list object
            head[0].set('id', prefix)
        except:
            return False
        return True
    
    def getTexts(self):
        '''
        Returns a reference to the list of text objects.
        '''
        return self.texts_list[:]
    
    def removeText(self, text_obj, undo_stack=None, undo_text=None, undo_pg=1):
        '''
        Removes the specified text from the document.
        '''
        if text_obj in self.texts_list:
            if undo_stack is not None:
                undo_stack.insert(0, ['REMOVE_TEXT', text_obj, text_obj.node.__deepcopy__(False),
                                      self.texts_list.index(text_obj),
                                      text_obj.node.getparent().index(text_obj.node),
                                      text_obj.node.getparent(), undo_text, undo_pg, _(u'Desfazer exclusão do texto.')])
            text_obj.node.getparent().remove(text_obj.node)
            self.texts_list.remove(text_obj)
            for el in text_obj.elements_list:
                text_obj.excludeFromObjectLists(el)
    
    def getMetadata(self):
        '''
        Returns a dictionary with Metadata information.
        '''
        metadata = {}

        # Read information from metadata nodes
        head_node = self.etree.getroot().find('head')
        for metadata_node in head_node.iterdescendants(tag='metadata'):
            g = metadata_node.get('generation')
            if g is not None:
                metadata[g] = []
                for meta_node in metadata_node.iterdescendants('meta'):
                    name_node = meta_node.find('n')
                    val_node = meta_node.find('v')
                    if name_node is not None:
                        # A tuple for each (name,value) pair
                        if val_node is None:
                            metadata[g].append([name_node.text, ''])
                        else:
                            metadata[g].append([name_node.text, val_node.text])
            else:
                __builtin__.log(_(u'XML incorreto: propriedade \'generation\' é obrigatória.')+'\n')

        return metadata
        
    def setMetadata(self, metadata):
        '''
        Update the content of Metadata nodes based on the
        dictionary with metadata information.
        '''
        # Rebuild all metadata nodes
        head_node = self.etree.getroot().find('head')
        head_id = head_node.get('id')
        head_node.clear()
        if head_id is None:
            head_id = ""
        head_node.set('id', head_id)
        for key in metadata.keys():
            gen_meta = metadata[key]
            gen_node = etree.SubElement(head_node, 'metadata', generation=key)
            for meta in gen_meta:
                meta_node = etree.SubElement(gen_node, 'meta')
                name_node = etree.SubElement(meta_node, 'n')
                val_node = etree.SubElement(meta_node, 'v')
                name_node.text = meta[0]
                val_node.text = meta[1]
                
    def importOldXML(self, file_name):
        '''
        Tries to import and old format XML.
        '''
        try:
            parser = etree.XMLParser(attribute_defaults=True, dtd_validation=False, remove_blank_text=True)
            self.etree = etree.parse(file_name, parser)
            last_w = None
            body = self.etree.getroot().find('body')
            new_body = etree.Element('body')

            # Process nodes recursively
            self.buildNewText(body, new_body)
            self.etree.getroot().remove(body)
            self.etree.getroot().append(new_body)
            self._generateIDs(self.etree.getroot())
            self._build()

            # Internal metadata
            mdata = self.getMetadata()
            mdata['edictor_internal'] = []
            mdata['edictor_internal'].append(('Document Name','')) 
            mdata['edictor_internal'].append(('XML generated by','E-Dictor-v'+str(__builtin__.version)))
            mdata['edictor_internal'].append(('Last Saved Date',time.strftime('%d.%m.%Y', time.localtime())))
            mdata['edictor_internal'].append(('Word Count',''))
            self.setMetadata(mdata)

            self.modified = True
        except XMLValidationError:
            raise BaseException, (_(u"Erro: arquivo XML inválido: ") + str(sys.exc_info()[0]) + str(sys.exc_info()[1])).encode('utf-8')
        
    def buildNewText(self, old_body, new_body):
        # Gather a text version of all the content (with special word/editions treatment, see below)
        ed_types = []
        if __builtin__.cfg.get(u'Preferences', u'EditionTypes') != '':
            for ed in __builtin__.cfg.get(u'Preferences', u'EditionTypes').decode('utf-8').split(','):
                type, label = ed.split('|')
                ed_types.append(type)
        def_type = ''
        if len(ed_types) > 2:
            def_type = ed_types[-1]
        text = self.diggNode(old_body, def_type)
        new_text = etree.SubElement(new_body,'text')
        # Build structure for the text
        new_sec = self.generateSectionContent(text, ed_types)
        new_text.append(new_sec)
        return new_text

    def diggNode(self, node, def_type):
        text = ''
        if node.text: text += ' ' + node.text.strip()
        for child in node.getchildren():
            if callable(child):
                # <comment> ou/e <!-- --> ?
                continue
            if child.tag == 'ed_mark':
                # Prepares an edited word in the format: word@edType_edWord@...
                or_text = ''
                if child.text: or_text += child.text.strip()
                for el in child.iterdescendants(tag='or'):
                    if el.text: or_text += el.text.strip()
                    if el.getparent() != child and el.tail: or_text += el.tail.strip()
                if child.find('or'):
                    for el in child.find('or').getchildren():
                        if el.tail: or_text += el.tail.strip()
                ed_text = ''
                if or_text.find(' ') < 0: # Ignore multi-word editions
                    for el in child.iterdescendants(tag='ed'):
                        if el.get('t') is None or el.get('t') == '': el.set('t', def_type)
                        if el.text: 
                            ed_text += '@'+el.get('t').strip()[0:3]+'_'+el.text.strip().replace(' ','|')
                # Append word
                text += ' ' + or_text + ed_text
                if child.tail: text += ' ' + child.tail.strip()
                continue
            if child is None or child.tag == 'ad': # Not expected, but in any case ignored
                continue
            if child.tag == 'p' or\
                    (child.tag == 'sec' and child.get('t') and\
                     child.get('t') == 'title'):
                text += ' <p> '
            if child.tag == 'comment':
                if child.tail: text += ' ' + child.tail
                continue
                #text += ' <p> <comment> '
            if child.tag == 'text_el':
                if child.tail: text += ' ' + child.tail
                continue
            if child.tag == 's':
                text += ' <s> '
            if child.tag == 'sec' and child.get('t') and child.get('t') == 'pag':
                text += ' <pag> '
                if child.tail: text += ' ' + child.tail
                continue  # There is no content 
            text += ' ' + self.diggNode(child, def_type)
        if node.tail: text += ' ' + node.tail.strip()
        return text.replace('\n','')

    def generateSectionContent(self, text, ed_types):
        if text.strip() != '':
            # Break paragraphs at blanklines
            sec_el = etree.Element('sc')
            p_list = text.split(' <p> ')
            for p in p_list:
                p_el = self.generateParagraphContent(p, ed_types)
                if p_el is not None and len(p_el.getchildren()) > 0:
                    sec_el.append(p_el)
            return sec_el
        return None
    
    def generateParagraphContent(self, text, ed_types):
        if text.strip() != '':
            # Break paragraphs at blanklines
            if text.find('<comment>') < 0:
                p_el = etree.Element('p')
            else:
                # Comments: <comment> -> <p t='comment'>
                text = text.replace('<comment>','')
                p_el = etree.Element('p', t='comment')
            s_list = text.split(' <s> ')
            for s_text in s_list:
                if s_text[-1] not in ['.','!','?','\n']:
                    s_text = s_text + '\n'
                s_text = s_text + ' '
                for s in contrib_nltk.tokenize.regexp(s_text, r'(.+?)(\.\.)?[\.!?\n]+ '):
                    # Process words
                    s_el = self.generateSentenceContent(s, ed_types)
                    if s_el is not None and len(s_el.getchildren()) > 0:
                        p_el.append(s_el)
            return p_el
        return None
    
    def generateSentenceContent(self, text, ed_types):
        global last_w

        if text.strip() != '':
            s_el = etree.Element('s')
            # Trying a more "inteligent" (a bit dangerous) tokenization...
            page_bk = False
            text = text.strip()

            # Separate the final dot(s) (from the final word) with a blank space
            tmp = ''
            while text.endswith('.'):
                tmp += '.'
                text = text[0:len(text) - 1]
            if len(tmp) > 0:
                text += ' ' + tmp
                
            for tk in contrib_nltk.tokenize.regexp(text, r'[^\s]+'):
                if tk.strip() == '<pag>':
                    page_bk = True
                    continue
                ed_list = tk.strip().split('@')
                for t in contrib_nltk.tokenize.regexp(ed_list[0], r'(\w+)?\$*(([\.,])?\d+)(([\.,])?\d+)?(([\.,])?\d+)?\$*|([\'~])?[\w\d]+([\.$\'~-])?([\w\d]+)?|(\.\.)?[^\w]'):
                    w_el = etree.Element('w')
                    or_el = etree.SubElement(w_el, 'o')
                    or_el.text = t
                    # Page break (if any)
                    if page_bk:
                        bk_el = etree.SubElement(or_el,'bk',t='p')
                        page_bk = False
                    # Editions, if any
                    for ed in ed_list[1:]:
                        ed_type, ed_text = ed.split('_')
                        if ed_type in ed_types and len(ed_text) > 0:
                            ed_el = etree.SubElement(w_el, 'e', t=ed_type)
                            ed_el.text = ed_text.replace('|',' ')
                        if ed_type in ['fon'] and len(ed_text) > 0:
                            ed_el = etree.SubElement(w_el, 'f')
                            ed_el.text = ed_text.replace('|',' ')
                    ed_list[1:] = []
                    last_w = w_el
                    s_el.append(w_el)
            return s_el
        return None

    def undoEdition(self, cur_text, op, do_stack, undo_info, main_frame):
        '''
        Undo a edition based on 'undo_info' array:
            [0]    --> Operation identifier
            [1..N] --> Specific operation information
            
            op       --> 0. Undo  : 1. Redo
            do_stack --> 'undo_stack' on 'redo' : 'redo_stack' on 'undo'
        '''
        rt = None

        word = main_frame.graphy_word_editing
        op_repl = [_(u'Refazer'),_(u'Desfazer')][op]
        op_desc = [_(u'Desfazer'),_(u'Refazer')][op]

        if undo_info[0] in ['BREAK','REMOVE_BK']:
            '''
            Undo info content: 
                [1] = Word Obj (current)
                [2] = Word node copy (before break insertion)
                [3] = Break node copy
                [3] = Word Obj index (in parent obj)
                [4] = Word node index (in parent node)
            '''
            cur_w_obj  = undo_info[1]
            s_obj = cur_text.getElementByRef(cur_w_obj.getParent().node.get('id'))
            node_to_restore = undo_info[2]
            new_w_obj  = Word(s_obj, node_to_restore, node_to_restore.get('id'))

            # Redo
            do_stack.insert(0, [undo_info[0], new_w_obj, undo_info[1].node.__deepcopy__(False), undo_info[3], undo_info[4],
                                undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
            
            # Replace word object (find by ID, cause instances may differ)
            ii = undo_info[3]
            s_obj.elements_list.remove(s_obj.elements_list[ii])
            s_obj.elements_list.insert(ii, new_w_obj)
            # Replace word node (find by ID, cause instances may differ)
            ii = undo_info[4]
            s_obj.node.remove(s_obj.node.getchildren()[ii])
            s_obj.node.insert(ii, node_to_restore)
            # Update lists
            cur_text.updateWordLists([cur_w_obj], [new_w_obj])
            cur_text.processPages()
           
            rt = new_w_obj

        elif undo_info[0] == 'W-EDIT':
            '''
            Undo info content: 
                [1] = List of Word Objects (before edition applying)
                [2] = Next Word (in case of 'junction') or None
            '''
            # Tuples (w_obj, w_node_copy, w_obj_index, w_node_index)
            undo_info[1].reverse()
            undo_info[2].reverse()
            u_list = []
            rmw_list = []
            for u_info in undo_info[1]:
                '''
                Undo info content: 
                    [0] = Word Obj (before edition)
                    [1] = Word node copy (before ...)
                    [2] = Word Obj index (in parent obj)
                    [3] = Word node index (in parent node)
                '''
                cur_w_obj  = u_info[0]
                s_obj = cur_text.getElementByRef(cur_w_obj.getParent().node.get('id'))
                old_w_node = u_info[1]
                new_w_obj  = Word(s_obj, old_w_node, old_w_node.get('id'))
                # Redo
                u_list.append((new_w_obj, u_info[0].node.__deepcopy__(False),
                               u_info[2], u_info[3]))

                # Replace word object (find by ID, cause instances may differ)
                ii = u_info[2]
                s_obj.elements_list.remove(s_obj.elements_list[ii])
                s_obj.elements_list.insert(ii, new_w_obj)
                # Replace word node (find by ID, cause instances may differ)
                ii = u_info[3]
                s_obj.node.remove(s_obj.node.getchildren()[ii])
                s_obj.node.insert(ii, old_w_node)
                # Update lists
                cur_text.updateWordLists([cur_w_obj], [new_w_obj])

                # Removed words
                if len(undo_info[2]) > 0:
                    el = undo_info[2].pop(0)
                    if isinstance(el, list):
                        # Restore the deleted (next) word
                        self.undoEdition(cur_text, 0, [], el, main_frame)
                        next_w = cur_text.getNextWord(new_w_obj,
                                        not isinstance(new_w_obj.getParent().getParent().getParent(), SectionElement))
                        rmw_list.append(next_w)
                    else:
                        # Delete the (next) word
                        next_w = el # cur_text.getWordByRef(el.getId())
                        el = [] # Undo stack
                        if cur_text.removeWord(next_w, el):
                            rmw_list.append(el[0])
                        else:
                            __builtin__.log(_(' Aviso! Palavra não encontrada para remoção.') +
                                            ' ('+el.getOriginalString()+') [undo:w-edit]\n')

            # Redo
            do_stack.insert(0, [undo_info[0], u_list, rmw_list, undo_info[-3], 
                                undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])

            cur_text.processPages()
            rt = word 

        elif undo_info[0] == 'EL-REMOVE':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Element Obj class name
                    [2] = Element node copy (before ...)
                    [3] = Element Obj index (in parent obj)
                    [4] = Element node index (in parent node)
                    [5] = Previous immediate word before element
                    [6] = Element Obj parent ref
                '''
                cur_el_obj  = undo_info[1]
                parent_obj = cur_text.getElementByRef(undo_info[6])
                old_el_node = undo_info[2]
    
                if cur_el_obj == 'Text':
                    new_el_obj = Text(old_el_node)
                else:
                    new_el_obj = eval(cur_el_obj.__class__.__name__+'(parent_obj, old_el_node)')
                    aux = eval('cur_text.'+__builtin__.el_type_dict[cur_el_obj.__class__.__name__])
                    aux[new_el_obj.getId()] = new_el_obj
                                        
                # Redo
                do_stack.insert(0, [undo_info[0], new_el_obj.node.get('id'), undo_info[-3], 
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Insert element object
                ii = undo_info[3]
                parent_obj.elements_list.insert(ii, new_el_obj)
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_el_obj.__class__.__name__])
                aux[new_el_obj.getId()] = new_el_obj
                if not isinstance(new_el_obj, Sentence): 
                    cur_text.buildObjectLists(new_el_obj.elements_list)
                # Insert element node
                ii = undo_info[4]
                parent_obj.node.insert(ii, old_el_node)
                # Update lists
                if undo_info[5] is None:
                    tmp_list = new_el_obj.getWordsList()
                    tmp_list.append(cur_text.words_list[0])
                    cur_text.updateWordLists([tmp_list[-1]], tmp_list)
                else: 
                    tmp_list = [cur_text.words_dict[undo_info[5].getId()]]
                    tmp_list.extend(new_el_obj.getWordsList())
                    cur_text.updateWordLists([tmp_list[0]], tmp_list)
                cur_text.processPages()
            else:
                # Redo
                cur_text.removeElementByRef(undo_info[1], do_stack, undo_info[-3], undo_info[-2])

        elif undo_info[0] == 'MERGE':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Element Obj (before merge)
                    [2] = Element node copy (before ...)
                    [3] = Previous Element Obj (before merge)
                    [4] = Previous Element node copy (before ...)
                    [5] = Element Obj index (in parent obj)
                    [6] = Element node index (in parent node)
                    [7] = Previous Element Obj index (in parent obj)
                    [8] = Previous Element node index (in parent node)
                '''
                cur_el_obj  = undo_info[1]
                cur_el_node = undo_info[2]
                if isinstance(cur_el_obj.getParent(), Text):
                    parent_obj = cur_el_obj.getParent()
                else:
                    parent_obj = cur_text.getElementByRef(cur_el_obj.getParent().node.get('id'))
                prev_el_obj = cur_text.getElementByRef(undo_info[3].getId())
                prev_el_node = undo_info[4]
                if isinstance(prev_el_obj.getParent(), Text):
                    parent_prev = prev_el_obj.getParent()
                else:
                    parent_prev = cur_text.getElementByRef(prev_el_obj.getParent().node.get('id'))
    
                new_el_obj = eval(cur_el_obj.__class__.__name__+'(parent_obj, cur_el_node)')
                new_prev_obj = eval(prev_el_obj.__class__.__name__+'(parent_prev, prev_el_node)')
                
                # Redo
                do_stack.insert(0, [undo_info[0], prev_el_obj, prev_el_obj.node.__deepcopy__(False),
                                    undo_info[7], undo_info[8], undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                
                # Update previous element (restore "left side")
                ii = undo_info[7]
                old_list = parent_prev.elements_list[ii].getWordsList()
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii])
                parent_prev.elements_list.remove(parent_prev.elements_list[ii])
                parent_prev.elements_list.insert(ii, new_prev_obj)
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_prev_obj.__class__.__name__])
                aux[new_prev_obj.getId()] = new_prev_obj
                if not isinstance(new_prev_obj, Sentence): 
                    cur_text.buildObjectLists(new_prev_obj.elements_list)
                ii = undo_info[8]
                parent_prev.node.remove(parent_prev.node.getchildren()[ii])
                parent_prev.node.insert(ii, prev_el_node)
                # Insert "right side" element
                ii = undo_info[5]
                parent_obj.elements_list.insert(ii, new_el_obj)
                ii = undo_info[6]
                parent_obj.node.insert(ii, cur_el_node)
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_el_obj.__class__.__name__])
                aux[new_el_obj.getId()] = new_el_obj
                if not isinstance(new_el_obj, Sentence): 
                    cur_text.buildObjectLists(new_el_obj.elements_list)
    
                # Update lists
                new_list = new_prev_obj.getWordsList()
                new_list.extend(new_el_obj.getWordsList())
                cur_text.updateWordLists(old_list, new_list)
            else:
                # Redo
                '''
                Redo info content: 
                    [1] = Sent/Parag Obj (reference to the current)
                    [2] = Sent/Parag node copy (before break)
                    [3] = Sent/Parag Obj index (in parent obj)
                    [4] = Sent/Parag node index (in parent node)
                '''
                cur_obj  = cur_text.getElementByRef(undo_info[1].getId())
                parent_obj = cur_text.getElementByRef(cur_obj.getParent().node.get('id'))
                old_node = undo_info[2]
                new_obj = eval(cur_obj.__class__.__name__+'(parent_obj, old_node)')
                ii = undo_info[3]
                next_obj_first_word = cur_text.getNextWord(cur_obj.getWordsList()[-1])
                if isinstance(cur_obj, Sentence):
                    next_obj = next_obj_first_word.getParent()
                else:
                    next_obj = next_obj_first_word.getParent().getParent()
                # Undo
                do_stack.insert(0, [undo_info[0], next_obj,
                                    next_obj.node.__deepcopy__(False),
                                    parent_obj.elements_list[ii],
                                    parent_obj.elements_list[ii].node.__deepcopy__(False),
                                    next_obj.getParent().elements_list.index(next_obj), 
                                    next_obj.node.getparent().getchildren().index(next_obj.node),
                                    undo_info[3], undo_info[4],
                                    undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Replace Sent/Parag object (find by ID, cause instances may differ)
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii])
                cur_text.excludeFromObjectLists(next_obj)
                parent_obj.elements_list.remove(parent_obj.elements_list[ii])
                parent_obj.elements_list.insert(ii, new_obj)
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_obj.__class__.__name__])
                aux[new_obj.getId()] = new_obj
                if not isinstance(new_obj, Sentence): 
                    cur_text.buildObjectLists(new_obj.elements_list)
                # Remove the next object
                old_list = cur_obj.getWordsList()
                old_list.extend(next_obj.getWordsList())
                next_obj.getParent().remove(next_obj)
                # Replace Sent/Parag node (find by ID, cause instances may differ)
                ii = undo_info[4]
                parent_obj.node.remove(parent_obj.node.getchildren()[ii])
                parent_obj.node.insert(ii, old_node)
                # Update lists
                cur_text.updateWordLists(old_list, new_obj.getWordsList())

            cur_text.processPages()

        elif undo_info[0] in ['CELL-PROP', 'INS_TEXT', 'HEAD_FOOT1']:
            '''
            Undo info content: 
                [1] = Element Obj (current)
                [2] = Element node copy (before operation)
                [3] = Element Obj index (in parent obj)
                [4] = Element node index (in parent node)
            '''
            cur_el_obj = undo_info[1]
            if not isinstance(cur_el_obj, Word):
                cur_el_obj = cur_text.getElementByRef(undo_info[1].getId())
            parent_obj = cur_text.getElementByRef(cur_el_obj.getParent().node.get('id'))
            old_el_node = undo_info[2]

            if not isinstance(cur_el_obj, Word):
                cl_name = cur_el_obj.__class__.__name__
                new_el_obj = eval(cl_name+'(parent_obj, old_el_node)')
            else:
                new_el_obj = Word(parent_obj, old_el_node, old_el_node.get('id'))

            # Redo
            do_stack.insert(0, [undo_info[0], new_el_obj, cur_el_obj.node.__deepcopy__(False), undo_info[3], undo_info[4],
                                undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
        
            # Replace element for the 'old' one
            ii = undo_info[3]
            if not isinstance(parent_obj.elements_list[ii], Word):
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii]) 
            parent_obj.elements_list.remove(parent_obj.elements_list[ii])
            parent_obj.elements_list.insert(ii, new_el_obj)
            if not isinstance(new_el_obj, Word): 
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_el_obj.__class__.__name__])
                aux[new_el_obj.getId()] = new_el_obj
                if not isinstance(new_el_obj, (Sentence, TextElement)): 
                    cur_text.buildObjectLists(new_el_obj.elements_list)
            ii = undo_info[4]
            parent_obj.node.remove(parent_obj.node.getchildren()[ii])
            parent_obj.node.insert(ii, old_el_node)

            # Update lists
            if not isinstance(cur_el_obj, Word):
                cur_text.updateWordLists(cur_el_obj.getWordsList(), new_el_obj.getWordsList())
            else:
                cur_text.updateWordLists([cur_el_obj], [new_el_obj])
                
            cur_text.processPages()
            
            if word is not None and word.getId() in cur_text.words_id:
                rt = word

        elif undo_info[0] in ['HEAD_FOOT2']:
            if op == 0:
                '''
                Undo info content: 
                    [1] = Parent Obj
                    [2] = Element Obj
                '''
                parent_obj = cur_text.getElementByRef(undo_info[1].getId())
                el_obj = cur_text.getElementByRef(undo_info[2].getId())
    
                # Redo
                do_stack.insert(0, [undo_info[0], parent_obj, el_obj, parent_obj.elements_list.index(el_obj),
                                    el_obj.node.getparent().getchildren().index(el_obj.node),
                                    undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                
                # Remove element
                parent_obj.remove(el_obj)
                cur_text.excludeFromObjectLists(el_obj)

                # Update lists
                cur_text.updateWordLists(el_obj.getWordsList(), [])
            else:
                '''
                Redo info content: 
                    [1] = Parent Obj
                    [2] = Element Obj (removed)
                    [3] = Index, in parent obj
                    [4] = Index, in parent node
                '''
                parent_obj = cur_text.getElementByRef(undo_info[1].getId())
                el_obj = undo_info[2]
    
                # Undo
                do_stack.insert(0, [undo_info[0], parent_obj, el_obj, undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                
                # Reinsert element
                old_list = parent_obj.getWordsList()
                parent_obj.elements_list.insert(undo_info[3], el_obj)
                parent_obj.node.insert(undo_info[3], el_obj.node)
                aux = eval('cur_text.'+__builtin__.el_type_dict[el_obj.__class__.__name__])
                aux[el_obj.getId()] = el_obj
                cur_text.buildObjectLists(el_obj.elements_list)

                # Update lists
                cur_text.updateWordLists(old_list, parent_obj.getWordsList())

            cur_text.processPages()

        elif undo_info[0] == 'SEC_END':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Section element
                    [2] = New section element
                '''
                sec_obj = cur_text.getElementByRef(undo_info[1].getId())
                new_sec = cur_text.getElementByRef(undo_info[2].getId())
    
                sec_node = sec_obj.node
                new_sec_node = new_sec.node
    
                # Redo
                do_stack.insert(0, [undo_info[0], new_sec_node.getchildren()[0].get('id'), undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])

                # Find text obj
                for t in main_frame.graphy.getTexts():
                    if t.node.get('id') == sec_obj.getParent().node.get('id'):
                        text_obj = t
    
                if text_obj is not None:
                    text_node = text_obj.node
        
                    # Objects: transfer objects (from new_sec) back to the section
                    for el in new_sec.getElements():
                        sec_obj.elements_list.append(el)
                        el.parent = sec_obj
                        sec_node.append(el.node)
        
                    # Remove 'new_sec'
                    text_obj.elements_list.remove(new_sec)
                    text_node.remove(new_sec_node)
                    del cur_text.sc_dict[new_sec.getId()] # Children must remain, cause they are not deleted
        
                    cur_text.processPages()
            else:
                # Redo
                cur_text.breakSection(undo_info[1], do_stack, undo_info[-3], undo_info[-2])

        elif undo_info[0] == 'TEXT_END':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Text element
                    [2] = New Text element
                    [3] = Undo for Section element ([SEC_END])
                '''
                text_obj = undo_info[1]
                new_text = undo_info[2]
    
                text_node = text_obj.node
                new_text_node = new_text.node
    
                # Redo
                do_stack.insert(0, [undo_info[0], new_text_node.getchildren()[0].getchildren()[0].get('id'),
                                    undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
    
                # Objects: transfer objects (from new_sec) back to the section
                old_list = cur_text.getWordsList()
                new_list = old_list[:]
                new_list.extend(new_text.getWordsList())
                cur_text.buildObjectLists(new_text.getElements())
                for el in new_text.getElements():
                    text_obj.elements_list.append(el)
                    el.parent = text_obj
                    text_node.append(el.node)
                cur_text.updateWordLists(old_list, new_list)
    
                # Undo section break (recursive)
                if undo_info[3] is not None:
                    self.undoEdition(cur_text, 0, [], undo_info[3][0], main_frame)
    
                # Remove new text
                main_frame.active_text = main_frame.graphy.getTexts().index(text_obj)
                main_frame.graphy.removeText(new_text)
    
                text_obj.processPages()
            else:
                # Redo
                cur_text.breakText(undo_info[1], main_frame.graphy, do_stack, undo_info[-3], undo_info[-2])

            # Menu
            main_frame.createDocumentTextsMenus()
            for m in main_frame.MenuDocSelText.GetMenuItems():
                if main_frame.menu_opts[m.GetId()] == main_frame.active_text:
                    m.Check(True)
                    break

        elif undo_info[0] == 'REMOVE_TEXT':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Text object
                    [2] = Text node copy
                    [3] = Text obj index in texts_list
                    [4] = Text node index in parent node
                    [5] = text node parent
                '''
                text_obj = undo_info[1]
                text_node = undo_info[2]
                text_obj.node = text_node
    
                # Redo
                do_stack.insert(0, [undo_info[0], undo_info[3], undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Replace Sent/Parag object (find by ID, cause instances may differ)
                ii = undo_info[3]
                main_frame.graphy.texts_list.insert(ii, text_obj)
                text_obj.buildObjectLists(text_obj.elements_list)
                # Replace Sent/Parag node (find by ID, cause instances may differ)
                ii = undo_info[4]
                undo_info[5].insert(ii, text_node)
    
                # Force E-Dictor to show the restored text
                main_frame.active_text = ii
                main_frame.createDocumentTextsMenus()
            else:
                # Redo
                main_frame.active_text = undo_info[1]
                main_frame.graphy.removeText(main_frame.graphy.getTexts()[undo_info[1]], do_stack, undo_info[-3], undo_info[-2])
                for k, v in main_frame.menu_opts.iteritems():
                    if main_frame.active_text == v:
                        del main_frame.menu_opts[k]
                        break
                main_frame.active_text = 0
                main_frame.createDocumentTextsMenus()
                for m in main_frame.MenuDocSelText.GetMenuItems():
                    if main_frame.menu_opts[m.GetId()] == main_frame.active_text:
                        m.Check(True)
                        break
            
        elif undo_info[0] == 'PG_NUM':
            if op == 0:
                '''
                Undo info content:
                    [1] = Original sentence obj
                    [2] = Orig. sentence node
                    [3] = Orig. sentence obj index
                    [4] = Orig. sentence node index
                    [5] = (Word (set as page number) ID, is_footer)
                    [6] = (paragraph_obj, obj_index, node_index, next_word)  (may be None)
                    [7] = SectionElement (if not inside <bk>)   (may be None)
                    [8] = True (sentence was deleted) or False (sentence was not deleted)
                    [9] = Undo information for the previous word (to which a break was added) (may be None) 
                '''
                cur_el_obj  = Sentence(cur_text.getElementByRef(undo_info[1].getParent().node.get('id')), undo_info[2])
                cur_el_node = undo_info[2]

                # Redo
                do_stack.insert(0, [undo_info[0], undo_info[5], undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                
                if undo_info[6] is not None:
                    # Restore Paragraph (excluded) that contained the Sentence that contained the Number
                    parent_obj = undo_info[6][0]
                    parent_obj.elements_list.append(cur_el_obj)
                    cur_el_obj.parent = parent_obj
                    parent_obj.node.append(cur_el_node)
                    cur_text.getElementByRef(parent_obj.getParent().node.get('id')).elements_list.insert(undo_info[6][1], parent_obj)
                    cur_text.getElementByRef(parent_obj.getParent().node.get('id')).node.insert(undo_info[6][2], parent_obj.node)
                    aux = eval('cur_text.'+__builtin__.el_type_dict[parent_obj.__class__.__name__])
                    aux[parent_obj.getId()] = parent_obj
                    cur_text.buildObjectLists(parent_obj.elements_list)
                    # Update lists (insert before the next element)
                    tmp = cur_el_obj.getWordsList()
                    tmp.append(undo_info[6][3])
                    cur_text.updateWordLists([undo_info[6][3]], tmp)
                else:
                    parent_obj = cur_text.getElementByRef(cur_el_obj.getParent().node.get('id'))
                    # Replace Sentence objects
                    ii = undo_info[3]
                    if not undo_info[8]:
                        removed_obj = parent_obj.elements_list[ii]
                        cur_text.excludeFromObjectLists(removed_obj)
                        parent_obj.elements_list.remove(removed_obj)
                    parent_obj.elements_list.insert(ii, cur_el_obj)
                    aux = eval('cur_text.'+__builtin__.el_type_dict[cur_el_obj.__class__.__name__])
                    aux[cur_el_obj.getId()] = cur_el_obj
                    ii = undo_info[4]
                    if not undo_info[8]:
                        parent_obj.node.remove(parent_obj.node.getchildren()[ii])
                    parent_obj.node.insert(ii, cur_el_node)
                    # Update lists
                    if not undo_info[8]:
                        cur_text.updateWordLists(removed_obj.getWordsList(), cur_el_obj.getWordsList())
                    else:
                        tmp_list = cur_el_obj.getWordsList()
                        tmp_list.extend(parent_obj.elements_list[ii+1].getWordsList())
                        cur_text.updateWordLists(parent_obj.elements_list[ii+1].getWordsList(), tmp_list)
    
                if undo_info[7] is not None:
                    # Remove SectionElement from Section
                    cur_text.getElementByRef(undo_info[7].getParent().node.get('id')).remove(undo_info[7])
                    cur_text.excludeFromObjectLists(undo_info[7])
                    cur_text.updateWordLists(undo_info[7].getWordsList(), [])

                if undo_info[9] is not None:
                    # Remove SectionElement from Section
                    self.undoEdition(cur_text, 0, [], undo_info[9], main_frame)

                # Fix node ID
                #cur_text.words_dict[undo_info[5][0]].node.set('id', undo_info[5][0])
    
                cur_text.processPages()
            else:
                # Redo
                cur_text.setWordAsPageNumber(cur_text.words_dict[undo_info[1][0]], undo_info[1][1], do_stack, undo_info[-3], undo_info[-2])

        elif undo_info[0] == 'INS_PG_NUM':
            if op == 0:
                '''
                Undo info content:
                    [1] = Word node
                    [2] = 0. Header   1.Footer
                    [3] = There was a prior page number? True/False
                '''
                if undo_info[3]:
                    # Redo
                    do_stack.insert(0, [undo_info[0], cur_text.getWordByRef(undo_info[1].get('id')).getString(), undo_info[2],
                                        undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                    
                    cur_text.insertPageNumber(undo_info[-2], undo_info[2], undo_info[1].find("o").text, None)
                else:
                    # Redo
                    do_stack.insert(0, [undo_info[0], undo_info[1].find("o").text, undo_info[2],
                                        undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                    
                    cur_text.removeWord(cur_text.getWordByRef(undo_info[1].get('id')), None, undo_info[-3], undo_info[-2])
            else:
                cur_text.insertPageNumber(undo_info[-2], undo_info[2], undo_info[1], do_stack, undo_info[-3])

        elif undo_info[0] in ['BK_S','BK_P']:
            if op == 0:
                '''
                Undo info content: 
                    [1] = Sent/Parag Obj (reference to the current)
                    [2] = Sent/Parag node copy (before break)
                    [3] = Sent/Parag Obj index (in parent obj)
                    [4] = Sent/Parag node index (in parent node)
                '''
                cur_obj  = cur_text.getElementByRef(undo_info[1].getId())
                parent_obj = cur_text.getElementByRef(cur_obj.getParent().node.get('id'))
                old_node = undo_info[2]
                new_obj = eval(cur_obj.__class__.__name__+'(parent_obj, old_node)')
                ii = undo_info[3]
                # Redo
                do_stack.insert(0, [undo_info[0], parent_obj.elements_list[ii],
                                    parent_obj.elements_list[ii].node.__deepcopy__(False),
                                    parent_obj.elements_list[ii+1],
                                    parent_obj.elements_list[ii+1].node.__deepcopy__(False),
                                    undo_info[3], undo_info[4], undo_info[-3],
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Replace Sent/Parag object (find by ID, cause instances may differ)
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii])
                parent_obj.elements_list.remove(parent_obj.elements_list[ii])
                parent_obj.elements_list.insert(ii, new_obj)
                # Remove the next object
                cur_text.updateWordLists(parent_obj.elements_list[ii+1].getWordsList(), [])
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii+1])
                parent_obj.remove(parent_obj.elements_list[ii+1])
                # Update object ID lists
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_obj.__class__.__name__])
                aux[new_obj.getId()] = new_obj
                if not isinstance(new_obj, Sentence):
                    cur_text.buildObjectLists(new_obj.elements_list)
                # Replace Sent/Parag node (find by ID, cause instances may differ)
                ii = undo_info[4]
                parent_obj.node.remove(parent_obj.node.getchildren()[ii])
                parent_obj.node.insert(ii, old_node)
                # Update lists
                cur_text.updateWordLists(cur_obj.getWordsList(), new_obj.getWordsList())
            else:
                '''
                Undo info content: 
                    [1] = Left Sent/Parag Obj (reference to the current)
                    [2] = Left Sent/Parag node copy (before break)
                    [3] = Right Sent/Parag Obj (reference to the current)
                    [4] = Right Sent/Parag node copy (before break)
                    [5] = Left Sent/Parag Obj index (in parent obj)
                    [6] = Left Sent/Parag node index (in parent node)
                '''
                cur_obj  = cur_text.getElementByRef(undo_info[1].getId())
                parent_obj = cur_text.getElementByRef(cur_obj.getParent().node.get('id'))
                old_lnode = undo_info[2]
                old_rnode = undo_info[4]
                new_lobj = eval(undo_info[1].__class__.__name__+'(parent_obj, old_lnode)')
                new_robj = eval(undo_info[3].__class__.__name__+'(parent_obj, old_rnode)')
                ii = undo_info[5]
                # Redo
                do_stack.insert(0, [undo_info[0], parent_obj.elements_list[ii],
                                    parent_obj.elements_list[ii].node.__deepcopy__(False),
                                    undo_info[5], undo_info[6], undo_info[-3], 
                                    undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Replace current Sent/Parag object by the left and right parts
                old_list = parent_obj.elements_list[ii].getWordsList()
                cur_text.excludeFromObjectLists(parent_obj.elements_list[ii])
                parent_obj.elements_list.remove(parent_obj.elements_list[ii])
                parent_obj.elements_list.insert(ii, new_lobj)
                parent_obj.elements_list.insert(ii+1, new_robj)
                aux = eval('cur_text.'+__builtin__.el_type_dict[new_robj.__class__.__name__])
                aux[new_lobj.getId()] = new_lobj
                aux[new_robj.getId()] = new_robj
                if not isinstance(new_robj, Sentence):
                    cur_text.buildObjectLists(new_lobj.elements_list)
                    cur_text.buildObjectLists(new_robj.elements_list)
                new_list = new_lobj.getWordsList()
                new_list.extend(new_robj.getWordsList())
                # Replace Sent/Parag node (find by ID, cause instances may differ)
                ii = undo_info[6]
                parent_obj.node.remove(parent_obj.node.getchildren()[ii])
                parent_obj.node.insert(ii, old_lnode)
                parent_obj.node.insert(ii, old_rnode)
                # Update lists
                cur_text.updateWordLists(old_list, new_list)

            cur_text.processPages()

        elif undo_info[0] == 'REMOVE_W':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Removed Word Obj (reference to the current)
                    [2] = Removed Word node copy (before break)
                    [3] = Removed Word Obj index (in parent obj)
                    [4] = Removed Word node index (in parent node)
                '''
                cur_obj  = undo_info[1]
                parent_obj = cur_text.getElementByRef(cur_obj.getParent().node.get('id'))
                old_list = parent_obj.getWordsList()
                old_node = undo_info[2]
                # Creates a new word, updating edition information
                new_w_obj = Word(parent_obj, old_node, old_node.get('id'))
                # Redo
                do_stack.insert(0, [undo_info[0], old_node.get('id'),
                                    undo_info[-3], undo_info[-2], undo_info[-1].replace(op_desc, op_repl)])
                # Replace Sent/Parag object (find by ID, cause instances may differ)
                ii = undo_info[3]
                parent_obj.elements_list.insert(ii, new_w_obj)
                # Replace Sent/Parag node (find by ID, cause instances may differ)
                ii = undo_info[4]
                parent_obj.node.insert(ii, old_node)
                # Update lists
                cur_text.updateWordLists(old_list, parent_obj.getWordsList())

                cur_text.processPages()
                rt = new_w_obj
            else:
                rt = cur_text.getNextWord(cur_text.words_dict[undo_info[1]], True)
                if rt is None:
                    rt = cur_text.getPreviousWord(cur_text.words_dict[undo_info[1]], True)
                cur_text.removeWord(cur_text.words_dict[undo_info[1]], do_stack, undo_info[-3], undo_info[-2])

        elif undo_info[0] == 'MOVE_W':
            if op == 0:
                '''
                Undo info content: 
                    [1] = Word Obj (reference to the current)
                    [2] = Forward [true/false]
                '''
                rt = cur_text.moveWord(cur_text.getWordByRef(undo_info[1].getId()), undo_info[2], do_stack, undo_info[-3], undo_info[-2])
            else:
                # Redo
                rt = cur_text.moveWord(cur_text.getWordByRef(undo_info[1].getId()), undo_info[2], do_stack, undo_info[-3], undo_info[-2])
        else:
            return False, _(u"A operação [") + undo_info[0] + _(u"] não pode ser desfeita.")
        
        return True, rt
