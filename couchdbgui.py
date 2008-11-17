import wx
import wx.lib.sized_controls as sc
from contextlib import contextmanager
import couchdb.schema as schema
import couchdb.client as client
from datetime import datetime
from couchdb import Server
import sys
import wx.lib.editor as ed
import wx.html as html

class Screenshot(object):
	def __init__(self, filename = "snap.png"):
        	self.filename = filename
        	try:
			p = wx.GetDisplaySize()
            		self.p = p
            		bitmap = wx.EmptyBitmap( p.x, p.y)
            		dc = wx.ScreenDC()
            		memdc = wx.MemoryDC()
            		memdc.SelectObject(bitmap)
            		memdc.Blit(0,0, p.x, p.y, dc, 0,0)
            		memdc.SelectObject(wx.NullBitmap)
            		bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG )
            
        	except:
            		self.filename = ""


class Post( schema.Document):
	author = schema.TextField()
	subject = schema.TextField()
	content = schema.TextField()
	tags = schema.ListField( schema.TextField() )
	comments = schema.ListField( schema.DictField(schema.Schema.build(
	comment_author = schema.TextField(),
	comment = schema.TextField(),
	comment_date = schema.DateTimeField()
	)))
	date = schema.DateTimeField()
					

class EditorValidator( wx.PyValidator ):
	def __init__( self, name, data):
		wx.PyValidator.__init__(self)
		self.name = name
		self.data = data

	def Clone( self):
		return NonEmptyValidator(self.name, self.data)

	def Validate(self, win):
		editor = self.GetWindow()
		text = editor.GetText()
		# a warning.  setting SetBackgroundColour in mac os x is useless, because the background color remains the same.
		if len(text) == 0:
			wx.MessageBox("{0} can't be empty!".format(self.name), caption="Validation Error")
			editor.SetBackgroundColour("pink")
			editor.SetFocus()
			editor.Refresh()
			return False
		else:
			editor.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
			editor.Refresh()
			return True

	def TransferToWindow( self):
		return True

	def TransferFromWindow( self):
		editor = self.GetWindow()
		value = editor.GetText()
		setattr( self.data, self.name.lower(), value) 
		
class NonEmptyValidator( wx.PyValidator):
	def __init__( self, name, data):
		wx.PyValidator.__init__(self)
		self.name = name
		self.data = data
		
	def Clone( self):
		return NonEmptyValidator(self.name, self.data)

	def Validate(self, win):
		textCtrl = self.GetWindow()
		text = textCtrl.GetValue()
		# a warning.  setting SetBackgroundColour in mac os x is useless, because the background color remains the same.
		if len(text) == 0:
			wx.MessageBox("{0} can't be empty!".format(self.name), caption="Validation Error")
			textCtrl.SetBackgroundColour("pink")
			textCtrl.SetFocus()
			textCtrl.Refresh()
			return False
		else:
			textCtrl.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
			textCtrl.Refresh()
			return True

	def TransferToWindow( self):
		return True

	def TransferFromWindow( self):
		tc = self.GetWindow()
		value = tc.GetValue()
		
		if self.name == "Tags":
			value = [x.upper() for x in value.split(",")]
			value = list(set(value))
			value.sort()

		setattr( self.data, self.name.lower(), value) 
		
		return True

class HtmlWindowViewer(html.HtmlWindow):
	def __init__(self, parent, id):
		 html.HtmlWindow.__init__(self, parent, id, style=wx.NO_FULL_REPAINT_ON_RESIZE)
				        

class DebugDialog( sc.SizedDialog):
	def __init__( self, message):
		sc.SizedDialog.__init__(self, None, -1 , "Debug Dialog",  size = ( 400,600 ), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY) # Tks to Robin Dunn for his advice on this...when using SizedDialog
		pane = self.GetContentsPane()
		pane.SetSizerType("form")
		self.pane = pane
		wx.StaticText( self.pane, -1, "Debug")
		text = wx.TextCtrl( self.pane, -1 , message, size = ( 300,-1) , style=wx.TE_MULTILINE )
		text.SetSizerProps( expand=True )
		self.SetButtonSizer( self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))
		self.Fit()
		self.SetMinSize(self.GetSize())

class User(object):
	username = None
	password = None

class Comment(object):
	comment = None

class LoginDialog( sc.SizedDialog ):
	def __init__( self , user=""):
		sc.SizedDialog.__init__(self, None, -1 , "Login Dialog", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY) # Tks to Robin Dunn for his advice on this...when using SizedDialog
		pane = self.GetContentsPane()
		pane.SetSizerType("form")
		self.user = user
	        self.ID_USERNAME = wx.NewId()	
		wx.StaticText(pane, -1, "User")
		user = wx.TextCtrl(pane, self.ID_USERNAME ,"", validator = NonEmptyValidator("username", self.user))
		user.SetSizerProps(expand=True)
		
		wx.StaticText(pane, -1, "Password")
		password = wx.TextCtrl(pane, -1 ,"", style=wx.TE_PASSWORD, validator = NonEmptyValidator("password", self.user))
		password.SetSizerProps(expand=True)
		self.Bind( wx.EVT_TEXT, self.OnText, id = self.ID_USERNAME)
		
		self.SetButtonSizer( self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))

		self.Fit()
		self.SetMinSize(self.GetSize())
		user.SetFocus()

	def OnText(self,event):
		id = event.GetId()
		if id == self.ID_USERNAME:
			t = self.FindWindowById( id )
			v = t.GetValue()
			v = v.upper()
			t.SetValue(v)
			lastposition = t.GetLastPosition()
			t.SetInsertionPoint(lastposition)

class EditorDialog(wx.Dialog):
	def __init__( self, foo = "" ):
		wx.Dialog.__init__(self, None, -1 , "EditorDialog",  size = ( 400,600 ), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		win = wx.Panel(self, -1)
		editor = ed.Editor(win, -1, style = wx.SUNKEN_BORDER )
		box = wx.BoxSizer(wx.VERTICAL)
		box.Add(editor, 1, wx.ALL|wx.GROW,1)
		win.SetSizer( box)
		win.SetAutoLayout( True )
		editor.SetText(["","Ejemplo","de editor"])
		std = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
		box.Add(std,1,wx.ALL| wx.GROW,1)
		self.Fit()
		self.SetMinSize(self.GetSize())



class PostDialog( sc.SizedDialog):
	def __init__( self, post, user = "" ):
		sc.SizedDialog.__init__(self, None, -1 , "Blog Post",  size = ( 400,600 ), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY) # Tks to Robin Dunn for his advice on this...when using SizedDialog
		pane = self.GetContentsPane()
		pane.SetSizerType("form")
		self.pane = pane
		self.post = post


		for c in ( ["Author", user, wx.TE_READONLY, NonEmptyValidator], ["Subject", "", None, NonEmptyValidator],  ["Content", "Type html content here", wx.TE_MULTILINE, NonEmptyValidator ], ["Tags","GENERAL",None,NonEmptyValidator ]):
			text = self.StaticAndText( c )
			if c[0] == "Subject":
				self.text = text

	        	
		self.SetButtonSizer( self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))
		self.Fit()
		self.SetMinSize(self.GetSize())
		self.text.SetFocus()
	
	def StaticAndText(self, params  ):
			
		name, _default, style, ValidatorClass  = params
		wx.StaticText(self.pane, -1, name)
		if ValidatorClass == EditorValidator:
			text = ed.Editor(self.pane, -1, style = style)
			text.SetText(_default)
			text.SetValidator(ValidatorClass(name, self.post))
			text.SetSizerProps( expand = True )
			return text

		if style:
			text = wx.TextCtrl(self.pane,-1, _default, style= style, validator = ValidatorClass(name, self.post))
		else:
			text = wx.TextCtrl(self.pane,-1, _default, validator = ValidatorClass(name, self.post))
			
		text.SetSizerProps( expand=True )
		return text

class CommentDialog( sc.SizedDialog):

	def __init__( self, comment ):
		sc.SizedDialog.__init__(self, None, -1 , "Blog Post",  size = ( 400,600 ), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY) # Tks to Robin Dunn for his advice on this...when using SizedDialog
		pane = self.GetContentsPane()
		pane.SetSizerType("form")
		self.pane = pane
		self.comment = comment
		for c in ( ["Comment", "Put your html comment here", wx.TE_MULTILINE, NonEmptyValidator],):
			text = self.StaticAndText( c )
			if c[0] == "Comment":
				self.text = text

		self.SetButtonSizer( self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))
		self.Fit()
		self.SetMinSize(self.GetSize())
		self.text.SetFocus()

	def StaticAndText( self, params  ):
			
		name, _default, style, ValidatorClass  = params
		wx.StaticText(self.pane, -1, name)

		if style:
			text = wx.TextCtrl(self.pane,-1, _default, style= style, validator = ValidatorClass(name, self.comment))
		else:
			text = wx.TextCtrl(self.pane,-1, _default, validator = ValidatorClass(name, self.comment))
			
		text.SetSizerProps( expand=True )
		return text
		
class CouchdbFrame( wx.Frame):
	URL = "http://172.16.25.106:5984"
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "Couchdb wxPython with python 2.6 demo", size = (800,600) )
		self.URL = wx.GetTextFromUser( "Couchdb URL", "Enter", default_value = self.URL, parent = None) 

		blog = wx.Menu()
		post = blog.Append(-1 , "Post")
		comment = blog.Append(-1 , "Comment")
		mb = wx.MenuBar()
		engine = wx.Menu()
		ID_MENU_LOGIN = 505
		login = engine.Append(ID_MENU_LOGIN,"Login", "")
		engine.Append(-1,"Local","", wx.ITEM_RADIO)
		engine.Append(-1,"Tunneled ( Remote )","Remote Connection to a Couchdb engine via tunnel", wx.ITEM_RADIO)
		engine.AppendSeparator()
		ID_MENU_EDITOR = 508
		editor = engine.Append( ID_MENU_EDITOR, "Edit")
		exit = engine.Append(-1, "&Exit")
		mb.Append( engine, "Engine")
		mb.Append( blog , "Blog")
		self.SetMenuBar(mb)
		self.Bind(wx.EVT_MENU, self.OnPost, post)
		self.Bind(wx.EVT_MENU, self.OnLogin,login)
		self.Bind(wx.EVT_MENU, self.OnEditor,id = ID_MENU_EDITOR)
		self.Bind(wx.EVT_MENU, self.OnComment, comment)
		self.Bind(wx.EVT_MENU, self.OnExit, exit)
		self.popup = wx.Menu()
		ID_POPUP_SHOW = wx.NewId()
		ID_POPUP_COMMENT = wx.NewId()
		ID_POPUP_SCREENSHOT = wx.NewId()
		self.popup.Append(ID_POPUP_SHOW, "Show Blog Post")
		self.popup.Append(ID_POPUP_COMMENT, "Comment about Post")
		self.popup.Append(ID_POPUP_SCREENSHOT, "Screenshot")
		self.Bind(wx.EVT_MENU, self.OnComment, id = ID_POPUP_COMMENT)
		self.Bind(wx.EVT_MENU, self.OnScreenshot, id = ID_POPUP_SCREENSHOT)
		self.panel = wx.Panel(self, -1)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.list = wx.ListCtrl(self.panel , -1, style= wx.LC_REPORT)
		self.sizer.Add( self.list, 1, wx.GROW)
		self.html = HtmlWindowViewer( self.panel, -1)
		#self.html.SetBackgroundColour( wx.Colour(255,255,192))
		self.sizer.Add( self.html, 1, wx.GROW)
		self.panel.SetSizer(self.sizer)
		self.panel.SetAutoLayout( True )
						
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnLCtrl,  self.list)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRightClick,  self.list)
		event = wx.CommandEvent( wx.wxEVT_COMMAND_MENU_SELECTED, ID_MENU_LOGIN)
		self.GetEventHandler().ProcessEvent( event )
		self.BuildListCtrl()	
		if self.user.username:
			self.list.SetSize(wx.Size(795,595))
			self.Refresh()
			w, h = self.list.GetSize() 
			#self.SetSize(wx.Size(w,h)) 

	def OnEditor(self,event):
		with dialog( dict(dialog = EditorDialog, foo = "")) as val:
			pass

	def OnComment(self, event):
		self.ShowCommentDialog()
		return

	def ShowCommentDialog(self):
		comment = Comment()
		with dialog( dict(dialog = CommentDialog,  comment = comment)) as val:
			try:
				self.blogpost 
			except:
				wx.MessageBox("Error trying to comment in a non selected item", caption = "Post Id")
				return

			s = Server(self.URL)
			blog = s["blog"]
			p = Post.load(blog, self.blogpost)
			p.comments.append(dict(comment_author = self.user.username, comment= comment.comment, comment_date = datetime.now() ) )
			p.store(blog)
			self.OnLCtrl(None)
		return

	def OnLCtrl(self, event):
		if not event is None:
			self.blogpost = self.list.GetItem( event.m_itemIndex,0).GetText()
		else:
			try:
				self.blogpost
			except:
				return
		s = Server(self.URL)
		blog = s["blog"]
		bpost = blog[self.blogpost]
		attachments = bpost.get("_attachments",[])
		p = Post.load(blog, self.blogpost)
		tags = p.tags
		tags.sort()
		mytags = " :: ".join(tags)
		myattachments = " :: ".join(attachments)
		if myattachments:
			myattachments = "Attachments : " + myattachments
		else:
			myattachments = "&nbsp;"
		image = "&nbsp;"
		images = []
		for a in attachments:
			if a.endswith(".jpeg") or a.endswith(".jpg") or a.endswith(".JPEG") or a.endswith(".JPG"):
				image = "<img src='{0}/blog/{1}/{2}' width=64 height=64>".format(self.URL, self.blogpost, a.replace(" ", "%20"))
				images.append(image)
		if len(images) > 1:
			image = "<br>".append(images)
		comments = []
		if len(p.comments) > 0:
			for comment in p.comments:
				comments.append(u"Comment by {0} --{1}-- <br>{2}".format(comment["comment_author"], comment["comment_date"], comment["comment"]))

		contents = u"<b><font color='#0000FA'>{0} - {1} [{4}]</font></b><br>{5}<hr><b><font color='#FC0000''>{2}</font></b><br>{6}<br><br>{3}<hr>{7}".format(p.author, p.date, p.subject, p.content, mytags, myattachments, image, u"<hr>".join(comments))
		self.html.SetPage(contents)
		#self.html.SetBackgroundColour( wx.Colour(255,255,192))
		self.html.Refresh()
		pass

	def OnRightClick( self, event):
		self.PopupMenu( self.popup )
		return

	def OnLogin(self, event):
		self.user = User()
		with dialog( dict(dialog = LoginDialog, user = self.user)) as val:
			"""
			do validation here
			"""
			if self.user.username == "SMARTICS" and self.user.password == "secret":
				pass
			else:
				self.user.username = None
		if not self.user.username:
			self.Close()
	
	def BuildListCtrl(self):
		"""
		Getting information from a couchdb database using a view 
		and populating a wx.ListCtrl
		"""
		if not self.user.username:
			return

		try:
			self.list
			self.list.ClearAll()
		except:
			pass
			
			

		title = "BlogId Date Author Subject"
		for i, colTitle in enumerate(title.split(" ")):
			self.list.InsertColumn(i, colTitle)

		s = Server(self.URL)
		#self.list.ClearAll()
		bl = s["blog"]
		posts = []
		view = "by_date"
		bg1 = wx.Colour(239,235,239)
		bg2 = wx.Colour(255, 207,99)
		blogview = bl.view("all/{0}".format(view), descending = True)
		for doc in blogview:
			index = self.list.InsertStringItem(sys.maxint, doc.value["_id"]) 
			bgcolor = bg1
			if index % 2 == 0:
				bgcolor = bg2
			self.list.SetItemBackgroundColour( index , bgcolor ) 
			self.list.SetStringItem( index, 1, doc.value["date"]) 
			self.list.SetStringItem( index, 2, doc.value["author"]) 
			self.list.SetStringItem( index, 3, doc.value["subject"]) 

		for i in range(4):
			self.list.SetColumnWidth(i, wx.LIST_AUTOSIZE)
		self.Refresh()
	
	def OnExit(self, event):
		self.Close()

	def OnScreenshot(self, event):

		sfile = "screenshot{0}".format(datetime.now())
		for x in " .-:":
			sfile = sfile.replace(x , "")
		sfile = "{0}.png".format(sfile)
		if wx.Platform == "__WXMSW__":
			screenshot = Screenshot(filename = sfile)
			wx.MessageBox("Screenshot geneated as file {0}".format(sfile), "Screenshot")

	def OnPost(self, event):
		try:
			self.user
		except:
			self.user = ""

		post = Post() 		
		with dialog(dict( dialog = PostDialog, post = post, user = self.user.username)) as val:
			if val == wx.ID_OK:
				post.date = datetime.now()
				try:
					s = Server(self.URL)
					blog = s["blog"]
					post.store(blog)
					wx.MessageBox("New Post has id ... {0}".format(post.id), caption = "Post Id")
					self.BuildListCtrl()
				except:
				
					wx.MessageBox("{0}".format("Local or tunneled Couchdb server \nis not running or blog database does not exist"), caption = "Oops")



	
@contextmanager
def dialog( params ):
	#@contextmanager restricts this function to receive one argument, that's why we place everything in a dict
	DialogClass = params["dialog"]
	params.pop("dialog")
	try:
		dlg = DialogClass(**params)
		dlg.CenterOnScreen()
		val = dlg.ShowModal()
		yield val
	except:
		raise
	else:
		dlg.Destroy()


if __name__ == "__main__":
	app = wx.PySimpleApp()
	f = CouchdbFrame()
	f.CenterOnScreen()
	f.Show()
	app.MainLoop()
