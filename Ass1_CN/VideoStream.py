import cv2
import os
import struct
class VideoStream:															#numFrame: total frames in video
	def __init__(self, filename):											#frameNum: the current frame is reading from file	
		self.filename = filename
		self.wholeVideo = []
		self.posAllFrame= []
		try:
			self.file = open(filename, 'rb')
			print ('-'*60 +  "\nVideo file : |" + filename +  "| read\n" + '-'*60)
		except:
			print ("read " + filename + " error")
			raise IOError
		self.frameNum = 0

	def nextFrame(self, forward=0 , backward =0 ):
		moveFrame=0
		"""Forward video"""
		if forward==1:
			if self.frameNum + self.fps > self.numFrame:
				print("OCER HERE !!!!")
				self.file.seek(self.posAllFrame[self.numFrame-2])
				self.frameNum = self.numFrame -1
			else:
				self.file.seek(self.posAllFrame[self.frameNum + self.fps])
				self.frameNum += self.fps
		"""Backward video"""
		if backward==1:
			if self.frameNum - self.fps < 0:
				self.file.seek(0)
				self.frameNum = 0
			else:
				self.file.seek(self.posAllFrame[self.frameNum - self.fps])
				self.frameNum -= self.fps
		"""Get next frame."""
		data = self.file.read(5)
		if data:
			framelength = int(data)
			data = self.file.read(framelength)
			self.frameNum += 1
			print ('-'*10 + "\nNext Frame (#" + str(self.frameNum) + ") length:" + str(framelength) + "\n" + '-'*10)
		return data

	def getPosFrame(self):
		currFrame=0
		framelgth=0
		if self.filename:
            # Get the framelength from the first 5 bits
			data = self.file.read(5)
			self.posAllFrame.append(0)
			while data:
				framelgth = int(data)
				self.file.read(framelgth)
				self.posAllFrame.append(self.file.tell())
				data = self.file.read(5)
		self.reset_frame()

	def getWholeVideo(self):
		"""Append to the list"""
		if self.filename:
            # Get the framelength from the first 5 bits
			data = self.file.read(5)
			if data:
				framelength = int(data)
				self.wholeVideo.append(framelength)
				data = self.file.read(framelength)
			return data

	def calNumFrames(self):
		"""Get total nimber of frame"""
		while self.getWholeVideo():
			pass
		self.numFrame = len(self.wholeVideo)
		self.file.close()
		self.file = open(self.filename, 'rb')
		return len(self.wholeVideo)

	def calFps(self):
		"""Get frame per second"""
		cap = cv2.VideoCapture("./{0}".format(self.filename))
		self.fps = int(cap.get(cv2.CAP_PROP_FPS))

	def calTotalTime(self):
		"""Get total time of video"""
		self.calNumFrames()
		self.calFps()
		self.totalTime= self.numFrame/ self.fps



	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum

	def reset_frame(self):
		"""restart the video"""
		self.file.seek(0)
		self.frameNum = 0

