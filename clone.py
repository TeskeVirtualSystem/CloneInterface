#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################
#      _______     ______         #  
#     |_   _\ \   / / ___|        #
#       | |  \ \ / /\___ \        #
#       | |   \ V /  ___) |       #
#       |_|    \_/  |____/        #
#                                 #
###################################
#         TVS DClone Tool         #
#      Version				1.0	    #
#	  By: Teske Virtual Systems    #
#	  This tool is release under   #
#     GPL license, for more       #
#   details see license.txt file  #
###################################
#    http://www.teske.net.br      #
###################################



import commands
import subprocess
import re
import threading
import signal
import signal
import sys
import os
import gtk

import time
import urllib
import cgi
import math

from simplejson import dumps as to_json
from simplejson import loads as from_json

from webgui import start_gtk_thread
from webgui import launch_browser
from webgui import synchronous_gtk_message
from webgui import asynchronous_gtk_message
from webgui import kill_gtk_thread

disks = []


def LoadDisks():
	global disks	
	x = commands.getstatusoutput("gksudo -D \"DClone Tool\" ./utils.sh")
	if x[0] != 0 and x[0] != 256:
		print "Este aplicativo precisa das permissões de administrador para funcionar!"
		label = gtk.Label("Este aplicativo precisa de permissões de administrador para funcionar.")
		dialog = gtk.Dialog("DClone Tool", None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		dialog.vbox.pack_start(label)
		label.show()
		dialog.run()
		dialog.destroy()
		sys.exit(1)
	dk	=	commands.getoutput("sudo ./utils.sh -g")
	
	dk = dk.split(',')
	for disk in dk:
		dsk = commands.getoutput("sudo ./utils.sh -s "+disk)
		model = commands.getoutput("sudo ./utils.sh -m "+disk)
		dsk = dsk.split(' ')
		print dsk
		if	dsk[1] == 'GB':
			dsk[0] = float(dsk[0]) * 1000
		elif	dsk[1] == 'KB':
			dsk[0] = float(dsk[0]) / 1000
		else:
			dsk[0] = float(dsk[0])
		dpk = (disk,dsk[0],model)
		disks.append(dpk)


def buffered(f):
    a = []
    while True:
        c = f.read(1)
        if c == '':
            break
        elif c == '\r':
            yield ''.join(a)
            a = []
        else:
            a.append(c)


class dcfldd:
	
	LINE_MATCH = re.compile(r'\[(.*)\% of (.*)Mb\] (.*) blocks \((.*)Mb\) written. (.*) remaining')

	def __init__(self, diskfrom, diskto, totalsize):
		global started_copy
		if not started_copy:
			cmdline = ['/usr/bin/sudo', '/usr/bin/dcfldd', 'sizeprobe=if', 'if='+diskfrom, 'of='+diskto]
			print "Iniciando copia de "+diskfrom+" para "+diskto+" no total de "+str(totalsize)+" Mb"
			self.process = subprocess.Popen(cmdline, stderr=subprocess.PIPE)
			self.thread = threading.Thread(target=self.watch, args=[self.process.stderr])
			self.thread.start()
			started_copy = True
			self.total = totalsize
		
	def kill(self):
		os.kill(self.process.pid, signal.SIGINT)

	def watch(self, f):
		global web_send
		for line in buffered(f):
			result = self.LINE_MATCH.match(line)
			
			if result:
				result = result.groups()
				percent = result[0]
				self.total = result[1]
				mb = result[3]
				time = result[4]
				sys.stdout.write('%s Mb / %s Mb (%s%% restantes)\r' % (mb, self.total, percent))
				sys.stdout.flush()
				web_send('updateProgress('+str(mb)+','+str(self.total)+', "'+time+'");');

class Global(object):
    quit = False
    @classmethod
    def set_quit(cls, *args, **kwargs):
        cls.quit = True

def nl2br(string, is_xhtml= True ):
    if is_xhtml:
        return string.replace('\n','<br />')
    else :
        return string.replace('\n','<br>')

def main():	
	global disks
	global browser
	global web_send
	global started_copy
	global dcfprocess
	global window

	dcfprocess = None
	start_gtk_thread()
	started_copy = False
	file = os.path.abspath('page.html')
	uri = 'file://' + urllib.pathname2url(file)
	browser, web_recv, web_send, window = synchronous_gtk_message(launch_browser)(uri,quit_function=Global.set_quit,echo=False,width=640,height=640)
	browser.connect("navigation-requested", on_navigation_requested)
	while not Global.quit:
		time.sleep(1)

def ProcessDiskData(line):
	linedata = line.split(None,6)
	while len(linedata) < 7:
		linedata.append('')
	return linedata

def ProcessType(type):
	return cgi.escape(type.replace('primary',"Primária").replace('extended',"Extendida").replace('logic',"Lógica"))
	
def BuildDiskDataHTML(data,disk):
	diskdata = GetLoadedDiskData(disk)
	base = 'Modelo: '+cgi.escape(diskdata[2])+'<BR>Tamanho total: '+str(diskdata[1])+' MB<BR><center><table width="502" border="0" cellpadding="0" cellspacing="0" style="color: #FFFFFF"> \
	<tr>	\
    <th width="34" height="19" valign="top">ID</td> \
    <th width="93" valign="top">Tamanho</td> \
    <th width="106" valign="top">Tipo</td> \
    <th width="160" valign="top">Sistema de Arquivos </td> \
    <th width="109" valign="top">Sinalizador</td> \
  </tr> '
	dk	=	data.split('\n')
	for line in dk:
		id, inicio, fim, tamanho, tipo, fs, sig = ProcessDiskData(line)
		base += '<tr><td height="19" valign="top"><center>'+id+'</center></td><td valign="top"><center>'+tamanho+'</center></td><td valign="top"><center>'+ ProcessType(tipo)+'</center></td><td valign="top"><center>'+fs.upper()+'</center></td><td valign="top"><center>'+sig+'</center></td></tr>'
	base += '</table></center>'
	return base.replace('\n','')

def OpenSaveFile():
	global window
	filename = None
	chooser = gtk.FileChooserDialog("Salvar imagem", window, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
	response = chooser.run()
	if response == gtk.RESPONSE_OK: filename = chooser.get_filename()
	chooser.destroy()
	return filename

def OpenLoadFile():
	global window
	filename = None
	chooser = gtk.FileChooserDialog("Abrir imagem", None ,gtk.FILE_CHOOSER_ACTION_OPEN,(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,  gtk.STOCK_OPEN, gtk.RESPONSE_OK))
	chooser.set_default_response(gtk.RESPONSE_OK)	
	chooser.set_modal(False)
	response = chooser.run()
	if response == gtk.RESPONSE_OK: 
		filename = chooser.get_filename()
	chooser.destroy()	
	return filename

def GetLoadedDiskData(disk):
	global disks
	for dsk in disks:
		if dsk[0] == disk:
			return dsk
	return (None,None,None)

def on_navigation_requested(view, frame, req, data=None):
	global dcfprocess
	uri = req.get_uri()
	scheme, function, data =uri.split(':', 2)
	if scheme == 'callback':
		print uri
		if function == '//loaddisks':
			for disk in disks:
				web_send('addDisk(\''+disk[0]+'\',\''+disk[2]+'\');');	
			#web_send('addDisk(\'RAW\',\'Arquivo\');');
		elif function == '//loaddiskdata':
			data = data.split(':')
			disk_data = commands.getoutput("sudo ./utils.sh -d "+data[1])
			
			#html_data = nl2br(cgi.escape(disk_data))
			html_data = BuildDiskDataHTML(disk_data,data[1])
			if data[0] == 'origem':
				web_send('setDisk(\''+html_data+'\',true)');
			else:
				web_send('setDisk(\''+html_data+'\',false)');
		elif function == '//startclone':
			data = data.split(':')
			origindata	=	GetLoadedDiskData(data[1])
			print "Disco Origem: "
			print origindata
			destindata	=	GetLoadedDiskData(data[2])
			print "Disco Destino: "
			print destindata
			print "Iniciando dcfldd para /dev/null"
			dcfprocess = dcfldd(data[1],data[2], origindata[1])
		elif function == '//selectfilesource':
			filename = OpenLoadFile()
			print filename
			if not filename == None:
				web_send('addDiskOrg(\''+filename+'\',\'RAW\');');
		elif function == '//selectfiledestiny':
			filename = OpenSaveFile()
			print filename
			if not filename == None:
				web_send('addDiskDest(\''+filename+'\',\'RAW\');');
		elif function == '//exit':
			sys.exit(0)
		return True
	else:
		return False

def my_quit_wrapper(fun):
    signal.signal(signal.SIGINT, Global.set_quit)
    def fun2(*args, **kwargs):
        try:
            x = fun(*args, **kwargs) # equivalent to "apply"
        finally:
            kill_gtk_thread()
            Global.set_quit()
            if dcfprocess != None:
               dcfprocess.kill()
            print "Saindo..."
        return x
    return fun2


if __name__ == '__main__': # <-- this line is optional
	LoadDisks()
	my_quit_wrapper(main)()


