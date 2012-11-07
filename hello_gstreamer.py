#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst

default_file = '/home/jason/Oregon_Painting_Society_2011-04-08.avi'


class CustomElement(gst.Element):
    """ A basic, buffer forwarding gstreamer element """

    #here we register our plugin details
    __gstdetails__ = (
        "CustomElement plugin",
        "CustomElement",
        "First attempt, stolen from elsewhere.", 
        "no@body.com")
    
    #source pad (template): we send buffers forward through here
    _srctemplate = gst.PadTemplate ('src',
        gst.PAD_SRC,
        gst.PAD_ALWAYS,
        gst.caps_new_any())

    #sink pad (template): we recieve buffers from our sink pad
    _sinktemplate = gst.PadTemplate ('sink',
        gst.PAD_SINK,
        gst.PAD_ALWAYS,
        gst.caps_new_any())
    
    #register our pad templates
    __gsttemplates__ = (_srctemplate, _sinktemplate)

    def __init__(self, *args, **kwargs):   
        #initialise parent class
        gst.Element.__init__(self, *args, **kwargs)
        
        #source pad, outgoing data
        self.srcpad = gst.Pad(self._srctemplate)
        
        #sink pad, incoming data
        self.sinkpad = gst.Pad(self._sinktemplate)
        self.sinkpad.set_setcaps_function(self._sink_setcaps)
        self.sinkpad.set_chain_function(self._sink_chain)
        
        #make pads available
        self.add_pad(self.srcpad)
        self.add_pad(self.sinkpad)
    
    def _sink_setcaps(self, pad, caps):
        #we negotiate our capabilities here, this function is called
        #as autovideosink accepts anything, we just say yes we can handle the
        #incoming data
        return True
    
    def _sink_chain(self, pad, buf):
        #this is where we do filtering
        #and then push a buffer to the next element, returning a value saying it was either successful or not.
		print "Here........FILTERING!!!...........(len=%d,buf=%s)" %(len(buf),buf)
		return self.srcpad.push(buf)
		#out = []
		#for i in range(len(buf)):
		#	if(i % 5000 == 0):
		#		#print "this guy %d," %(ord(buf[i][0]))
		#		out.append(chr(0))
		#	else:
		#		out.append(buf[i])
		#return self.srcpad.push(buf)
		#return self.srcpad.push(''.join(out))

#here we register our class with glib, the c-based object system used by gstreamer
gobject.type_register(CustomElement)

class CustomPlayer(object):
	def __init__(self, message_callback, sync_message_callback):
		self.player = gst.element_factory_make("playbin2", "player")
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect("message", self._on_message)
		bus.connect("sync-message::element", self._on_sync_message)

		my_bin = gst.Bin("my-bin")
		timeoverlay = gst.element_factory_make("timeoverlay")
		my_bin.add(timeoverlay)
		pad = timeoverlay.get_pad("video_sink")
		ghostpad = gst.GhostPad("sink", pad)
		my_bin.add_pad(ghostpad)

		custom = CustomElement()
		my_bin.add(custom)

		autovideosink = gst.element_factory_make("autovideosink")
		my_bin.add(autovideosink)

		gst.element_link_many(timeoverlay, custom, autovideosink)
		self.player.set_property("video-sink", my_bin)

		self.message_callback = message_callback
		self.sync_message_callback = sync_message_callback

	def start(self, filepath):
		self.player.set_property("uri", "file://" + filepath)
		self.player.set_state(gst.STATE_PLAYING)

	def stop(self):
		self.player.set_state(gst.STATE_NULL)

	def _on_message(self, bus, message):
		print "DEBUG on_message: %s" %(message.type)
		if message.type in [gst.MESSAGE_EOS, gst.MESSAGE_ERROR]:
			self.stop()
		if message.type == gst.MESSAGE_ERROR:
			err, debug = message.parse_error()
			print "Error: %s" % err, debug
		self.message_callback(bus, message)

	def _on_sync_message(self, bus, message):
		if message.structure is None:
			return
		self.sync_message_callback(bus, message)

class GtkMain:
	
	def __init__(self):
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.set_title("Video-Player")
		window.set_default_size(500, 400)
		window.connect("destroy", gtk.main_quit, "WM destroy")
		vbox = gtk.VBox()
		window.add(vbox)
		hbox = gtk.HBox()
		vbox.pack_start(hbox, False)
		self.entry = gtk.Entry()
		self.entry.set_text(default_file)
		hbox.add(self.entry)
		self.button = gtk.Button("Start")
		hbox.pack_start(self.button, False)
		self.button.connect("clicked", self.start_stop)
		self.movie_window = gtk.DrawingArea()
		vbox.add(self.movie_window)
		window.show_all()
		self.player = CustomPlayer(self.on_message, self.on_sync_message)
		
	def start_stop(self, w):
		if self.button.get_label() == "Start":
			filepath = self.entry.get_text()
			if os.path.isfile(filepath):
				self.button.set_label("Stop")
				self.player.start(filepath)
		else:
			self.player.stop()
			self.button.set_label("Start")
						
	def on_message(self, bus, message):
		if message.type in [gst.MESSAGE_EOS, gst.MESSAGE_ERROR]:
			self.button.set_label("Start")
	
	def on_sync_message(self, bus, message):
		message_name = message.structure.get_name()
		if message_name == "prepare-xwindow-id":
			imagesink = message.src
			imagesink.set_property("force-aspect-ratio", True)
			gtk.gdk.threads_enter()
			imagesink.set_xwindow_id(self.movie_window.window.xid)
			gtk.gdk.threads_leave()
			
GtkMain()
gtk.gdk.threads_init()
gtk.main()
