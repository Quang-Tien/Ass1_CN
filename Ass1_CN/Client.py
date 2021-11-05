#__author__ = 'Tibbers'
from tkinter import *
import tkinter.messagebox as messagebox 
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:

	SETUP_STR = 'SETUP'
	SETUP_STR = 'SETUP'
	PLAY_STR = 'PLAY'
	PAUSE_STR = 'PAUSE'
	TEARDOWN_STR = 'TEARDOWN'
	EXIT_STR = 'EXIT'
	DESCRIBE_STR = 'DESCRIBE'
	FORWARD_STR = 'FORWARD'
	BACKWARD_STR = 'BACKWARD'
#state
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
# request
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	EXIT = 4
	DESCRIBE = 5
	FORWARD = 6
	BACKWARD = 7

	RTSP_VER = "RTSP/1.0"
	TRANSPORT = "RTP/UDP"
	backsignal=0
	forsignal=0
	counter = 0
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.setupMovie()

	def createWidgets(self):
		"""Build GUI."""
		# Create Describe button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = chr(8505)
		self.setup["command"] = self.describeInfo
		self.setup.grid(row=2, column=2, padx=2, pady=2)

		# Create Play button
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = chr(9654)
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=0, padx=2, pady=2)

		# Create Pause button
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = chr(9208)
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=1, padx=2, pady=2)

		# Create Forward button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = chr(9193)
		self.setup["command"] = self.forwardVideo
		self.setup.grid(row=2, column=1, padx=2, pady=2)

		# Create Backward button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = chr(9194)
		self.setup["command"] = self.backwardVideo
		self.setup.grid(row=2, column=0, padx=2, pady=2)

		# Create Stop button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = chr(9209) #==Teardown
		self.teardown["command"] =  self.teardownMovie
		self.teardown.grid(row=1, column=2, padx=2, pady=2)

		# Create Exit button
		self.exit = Button(self.master, width=20, padx=3, pady=3)
		self.exit["text"] = "Exit"
		self.exit["command"] =  self.exitClient
		self.exit.grid(row=1, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	def teardownMovie(self):
		"""Stop button handler."""
		if self.state !=self.INIT:
			self.sendRtspRequest(self.TEARDOWN)
			try:
				rate = float(self.counter/self.frameNbr)
			except: 
				rate=0
			print ('-'*60 + "\nRTP Packet Loss Rate :" + str(rate) +"\n" + '-'*60)

	def exitClient(self):
		"""Exit button handler."""
		self.sendRtspRequest(self.EXIT)
		#self.handler()
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
		try:
			rate = float(self.counter/self.frameNbr)
		except: 
			rate=0
		print ('-'*60 + "\nRTP Packet Loss Rate :" + str(rate) +"\n" + '-'*60)
		sys.exit(0)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)

	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			print ("Playing Movie")
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	def describeInfo(self):
		"""describe button handler."""
		# Create a new thread to listen for RTP packets
		print ("Describe video info")
		self.sendRtspRequest(self.DESCRIBE)

	def forwardVideo(self):
		if self.state !=self.INIT:
			print("Forward video....")
			self.sendRtspRequest(self.FORWARD)

	def backwardVideo(self):
		if self.state !=self.INIT:
			print("Backward video....")
			self.sendRtspRequest(self.BACKWARD)

	def listenRtp(self):
		while True:
			try:
				data,addr = self.rtpSocket.recvfrom(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					if rtpPacket.payload == bytearray(1):
						print('Stop listen RTP from server !!')
						#self.playEvent.set()
						#self.state=self.READY
						self.teardownMovie()

						break
					print ("||Received Rtp Packet #" + str(rtpPacket.seqNum()) + "|| ")
					try:
						if self.frameNbr + 1 != rtpPacket.seqNum() and (self.backsignal==1 ^ self.forsignal==1) :
							self.counter += 1
							print ('!'*60 + "\nPACKET LOSS\n" + '!'*60)
						currFrameNbr = rtpPacket.seqNum()
						#version = rtpPacket.version()
					except:
						print ("seqNum() error")
						print ('-'*60)
						traceback.print_exc(file=sys.stdout)
						print ('-'*60)

					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
					print('currframe: ', currFrameNbr, ' frameNbr: ',self.frameNbr)
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet():
					break
				print ("Didn`t receive data!")
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
			self.backsignal=0
			self.forsignal=0

	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""

		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

		try:
			file = open(cachename, "wb")
		except:
			print ("file open error")

		try:
			file.write(data)
		except:
			print ("file write error")

		file.close()

		return cachename

	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		try:
			photo = ImageTk.PhotoImage(Image.open(imageFile))
		except:
			print ("photo error")
			print ('-'*60)
			traceback.print_exc(file=sys.stdout)
			print ('-'*60)

		self.label.configure(image = photo, height=288)
		self.label.image = photo

	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""
		#-------------
		# TO COMPLETE
		#-------------

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "SETUP " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 RTP/UDP " + str(self.rtpPort)
			request = "%s %s %s" % (self.SETUP_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % (self.rtspSeq)
			request+="\nTransport: %s; client_port= %d" % (self.TRANSPORT,self.rtpPort)
			#self.rtspSocket.send(request.encode())
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.SETUP
			print('Request la:', request)

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "PLAY " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.PLAY_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId
			#self.rtspSocket.send(request)
			print ('-'*60 + "\nPLAY request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "PAUSE " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.PAUSE_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId	
			#self.rtspSocket.send(request)
			print ('-'*60 + "\nPAUSE request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PAUSE

		# Resume request


		# Teardown request
		elif requestCode == self.TEARDOWN and self.state != self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "TEARDOWN " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.TEARDOWN_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			#self.rtspSocket.send(request)
			print ('-'*60 + "\nTEARDOWN request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.TEARDOWN

		# Exit request
		elif requestCode == self.EXIT and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "EXIT " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.EXIT_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			#self.rtspSocket.send(request)
			print ('-'*60 + "\nEXIT request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.EXIT
		elif requestCode == self.DESCRIBE:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "EXIT " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.DESCRIBE_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			self.requestSent = self.DESCRIBE
		
		elif requestCode == self.FORWARD:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "EXIT " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.FORWARD_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			self.forsignal=1
			
			self.requestSent = self.FORWARD

			
		elif requestCode == self.BACKWARD:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			##request = "EXIT " + "\n" + str(self.rtspSeq)
			request = "%s %s %s" % (self.BACKWARD_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			self.backsignal=1

			self.requestSent = self.BACKWARD

		else:
			return

		# Send the RTSP request using rtspSocket.
		# ...
		self.rtspSocket.send(request.encode())
#		print '\nData sent:\n' + request

	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)

			if reply:
				self.parseRtspReply(reply)

			# Close the RTSP socket upon requesting Exit
			if self.requestSent == self.EXIT :
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break

	def parseRtspReply(self, data):
		print ("Parsing Received Rtsp data...")

		"""Parse the RTSP reply from the server."""
		lines = data.decode().split('\n')
		print(lines)
		seqNum = int(lines[1].split(' ')[1])
		self.protocol= lines[0].split(' ')[0]
		self.session = lines[2].split(' ')[1]
		self.currframe= lines[3].split(' ')[1]
		self.vidlen= lines[4].split(' ')[1]
		self.fps= lines[5].split(' ')[1]
		self.frames= lines[6].split(' ')[1]
		describe = "Protocol version number: " + self.protocol+\
		"\nSession: " + self.session +\
		"\nCurr Frame: " + self.currframe +\
		"\nVideo Len: " + self.vidlen +\
		"\nFPS: " + self.fps +\
		"\nTotal Frames: " + self.frames
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session

			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						print ("Updating RTSP state...")
						# self.state = ...
						self.state = self.READY
						# Open RTP port.
						#self.openRtpPort()
						print ("Setting Up RtpPort for Video Stream")
						self.openRtpPort()
						#self.reset_init(self, master, serveraddr, serverport, rtpport, filename)

					elif self.requestSent == self.PLAY:
						 self.state = self.PLAYING
						 print ('-'*60 + "\nClient is PLAYING...\n" + '-'*60)

					elif self.requestSent == self.PAUSE:
						 self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						 self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# self.state = ...
						self.state = self.READY
						self.playEvent.set()
						self.frameNbr=0
						# Flag the teardownAcked to close the socket.
						#self.teardownAcked = 1
						#self.reset_init(self.master, self.serverAddr, self.serverPort, self.rtpPort, self.fileName)

					elif self.requestSent == self.EXIT:
						# self.state = ...
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1

					elif self.requestSent == self.DESCRIBE:
						self.playEvent.set()
						self.pauseMovie()
						messagebox.showinfo(title='Information', message=describe)
						print ("Playing Movie")
						self.playMovie()
					elif self.requestSent == self.FORWARD:
						if self.state == self.PLAYING:
							if self.frameNbr +int(self.fps) > int(self.frames):
								self.frameNbr = int(self.frames)-2
							else :
								self.frameNbr += int(self.fps)
					elif self.requestSent == self.BACKWARD:
						if self.state == self.PLAYING:
							if self.frameNbr -int(self.fps) > 0:
								self.frameNbr -= int(self.fps)+1
							else :
								self.frameNbr=0

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...


		# Set the timeout value of the socket to 0.5sec
		# ...
		self.rtpSocket.settimeout(0.5)
#		try:
			# Bind the socket to the address using the RTP port given by the client user
			# ...
#		except:
#			tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

		try:
			#self.rtpSocket.connect(self.serverAddr,self.rtpPort)
			self.rtpSocket.bind(('',self.rtpPort))   # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
			#self.rtpSocket.listen(5)
			print ("Bind RtpPort Success")

		except:
			messagebox.showwarning('Connection Failed', 'Connection to rtpServer failed...')


	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			#self.playMovie()
			print ("Playing Movie")
			threading.Thread(target=self.listenRtp).start()
			#self.playEvent = threading.Event()
			#self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
