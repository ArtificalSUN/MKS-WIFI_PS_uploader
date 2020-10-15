import sys, os, time, io
import tkinter as tk
import socket as pysock
import requests


class MKS_relay:
    def __init__(self, addr, port, ExtBar, wintitle):
        self.printUploaded = True
        self.address = addr
        self.port = port
        self.socket = pysock.socket(pysock.AF_INET, pysock.SOCK_STREAM)
        self.recv_buf = 8194
        self.isConnected = False
        self.debug = False
        self.ExtBar = ExtBar
        self.wintitle = wintitle
        self.status = ""

        self.printing_filename = ""
        self.job_state = ""
        self.printing_time = 0
        self.totaltime = 0
        self.tm  = 0
        self.mms = 0
        self.printing_progress = 0.0
        self.last_upd_time = 0
        self.last_upd_time = 0
        self.isPrinting = False
        self.isPaused = False
        self.SDfiles = []
        self.readingSDfiles = False

        self.local_filename = ""
        self.sd_filename = ""
        self.SDfiles = []

        self.t0_temp = ''
        self.t1_temp = ''
        self.bed_temp = ''
        self.t0_nowtemp = 0.0
        self.t0_targettemp = 0.0
        self.t1_nowtemp = 0.0
        self.t1_targettemp = 0.0
        self.bed_nowtemp = 0.0
        self.bed_targettemp = 0.0

        self.post_multi_part = None
        self.post_part = None
        self.post_reply = None

    def relay_start(self):
        if self.debug: print((self.address, self.port)); print("Connecting to {}:{}".format(self.address, self.port))
        try:
            self.socket.connect((self.address, self.port))
            self.isConnected = True
        except Exception as e:
            print(e)
            raise(e)

    def relay_stop(self):
        if self.debug: print("Disconnecting from {}:{}".format(self.address, self.port))
        try:
            self.socket.shutdown(pysock.SHUT_RDWR)
            self.socket.close()
            self.isConnected = False
        except Exception as e:
            print(e)
            raise(e)

    def upload(self):
        with open(self.local_filename, 'r') as f:
            gcode = f.read()
        body_buffer = BufferReader(gcode.encode(), self.upload_progress)
        r = requests.post("http://{:s}/upload?X-Filename={:s}".format(self.address, self.sd_filename), data=body_buffer, headers={'Content-Type': 'application/octet-stream', 'Connection' : 'keep-alive'})
        print("Request code: %s" % r.text)
        if self.printUploaded:
            self.printFile()

    # def upload_finished(self, reply):
    #     http_status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    #     if self.printUploaded:
    #         self.printFile()
    #     if not http_status_code:
    #         return


    def printFile(self):
        self.sendCommand("M23 " + self.sd_filename)
        self.sendCommand("M24")

    def updateExtBar(self, prog):
        self.ExtBar['value'] = int(prog)

    def upload_progress(self, size, progress):
        if size > 0:
            prog_perc = progress*100/size
            print("Streaming bytes {0} / {1} ({2:.2f}%)".format(progress, size, prog_perc))
            self.updateExtBar(prog_perc)

    def upload_error(self, reply, sslerror):
        pass

    def retrieveSDfiles(self):
        self.sendCommand("M20")

    def sendCommand(self, cmd):
        if self.socket:
            if isinstance(cmd, str):
                self.socket.send((cmd + "\r\n").encode())
                if self.debug: print("Sending {}".format(cmd))
            elif isinstance(cmd, list):
                for eachCommand in cmd:
                    self.socket.send((eachCommand + "\r\n").encode())
                    if self.debug: print("Sending {}".format(eachCommand))

    def isBusy(self):
        return self.isPrinting or self.isPaused

    def readFromRelay(self):
        if not self.socket:
            self.relay_stop()
            return
        try:
            if not self.isConnected:
                self.isConnected = True
            rawdata = str(self.socket.recv(self.recv_buf), encoding=sys.getfilesystemencoding())
            # print(rawdata)
            lines = rawdata.splitlines(keepends=False)
            # print(lines)
            while len(lines)>0:
                s = lines.pop(0)
                s = s.replace("\r", "").replace("\n", "")
                # self.status = "Received: %s" %s
                # self.wintitle("MKS ASS @ {}:{} ".format(self.address, self.port)+self.status)
                if self.debug: print(s)
                if "T" in s and "B" in s and "T0" in s:
                    self.t0_temp = s[s.find("T0:") + len("T0:"):s.find("T1:")]
                    self.t1_temp = s[s.find("T1:") + len("T1:"):s.find("@:")]
                    self.bed_temp = s[s.find("B:") + len("B:"):s.find("T0:")]
                    self.t0_nowtemp = float(self.t0_temp[0:self.t0_temp.find("/")])
                    self.t0_targettemp = float(self.t0_temp[self.t0_temp.find("/") + 1:len(self.t0_temp)])
                    self.t1_nowtemp = float(self.t1_temp[0:self.t1_temp.find("/")])
                    self.t1_targettemp = float(self.t1_temp[self.t1_temp.find("/") + 1:len(self.t1_temp)])
                    self.bed_nowtemp = float(self.bed_temp[0:self.bed_temp.find("/")])
                    self.bed_targettemp = float(self.bed_temp[self.bed_temp.find("/") + 1:len(self.bed_temp)])
                    continue
                if s.startswith("M997"):
                    self.job_state = "offline"
                    if "IDLE" in s:
                        self.isPrinting = False
                        self.isPaused = False
                        self.job_state = 'idle'
                    elif "PRINTING" in s:
                        self.isPrinting = True
                        self.isPaused = False
                        self.job_state = 'printing'
                    elif "PAUSE" in s:
                        self.isPrinting = False
                        self.isPaused = True
                        self.job_state = 'paused'
                    continue
                if s.startswith("M994"):
                    if self.isBusy() and s.rfind("/") != -1:
                        self.printing_filename = s[s.rfind("/") + 1:s.rfind(";")]
                    else:
                        self.printing_filename = ""
                    continue
                if s.startswith("M992"):
                    if self.isBusy():
                        self.tm = s[s.find("M992") + len("M992"):len(s)].replace(" ", "")
                        self.mms = self.tm.split(":")
                        self.printing_time = int(self.mms[0]) * 3600 + int(self.mms[1]) * 60 + int(self.mms[2])
                    else:
                        self.printing_time = 0
                    continue
                if s.startswith("M27"):
                    if self.isBusy():
                        self.printing_progress = float(s[s.find("M27") + len("M27"):len(s)].replace(" ", ""))
                        self.totaltime = self.printing_time/self.printing_progress*100
                    else:
                        self.printing_progress = 0
                        self.totaltime = self.printing_time * 100
                    continue
                if 'Begin file list' in s:
                    self.readingSDfiles = True
                    self.SDfiles = []
                    self.last_upd_time = time.time()
                    continue
                if 'End file list' in s:
                    self.readingSDfiles = False
                    continue
                if self.readingSDfiles:
                    s = s.replace("\n", "").replace("\r", "")
                    if s.lower().endswith(".gcode") or s.lower().endswith(".gco") or s.lower().endswith(".g"):
                        self.SDfiles.append(s)
                    continue
        except Exception as e:
            print(e)

class CancelledError(Exception):
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return self.msg

    __repr__ = __str__


class BufferReader(io.BytesIO):
    def __init__(self, buf=b'', callback=None, cb_args=(), cb_kwargs={}):
        self._callback = callback
        self._cb_args = cb_args
        self._cb_kwargs = cb_kwargs
        self._progress = 0
        self._len = len(buf)
        io.BytesIO.__init__(self, buf)

    def __len__(self):
        return self._len

    def read(self, n=-1):
        chunk = io.BytesIO.read(self, n)
        self._progress += int(len(chunk))
        self._cb_kwargs.update({
            'size'    : self._len,
            'progress': self._progress
        })
        if self._callback:
            try:
                self._callback(*self._cb_args, **self._cb_kwargs)
            except: # catches exception from the callback
                raise CancelledError('The upload was cancelled.')
        return chunk
