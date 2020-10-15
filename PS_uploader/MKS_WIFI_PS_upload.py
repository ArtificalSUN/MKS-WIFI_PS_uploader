#! /usr/bin/env python
#  -*- coding: utf-8 -*-
# author: Victor Shapovalov (@ArtificalSUN), 2020
# version: 0.1.0

import sys, os, time, io
# import tkinter as tk
import socket as pysock
# import urllib3
import requests

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

def progress(size=None, progress=None):
    # print("Streaming bytes {0} / {1} ({2}%)".format(progress, size, int(progress*100/size)))
    showstatus("Uploading %s bytes" % size, progress, size)

def showstatus(line, cur, tot, bar = 20):
    if cur>tot: pass
    else:
        block = int(round(bar*cur/tot))
        sys.stdout.write("\r{}: [{}] {:3.1f}%".format(line, "#"*block + " "*(bar-block), cur/tot*100))
        sys.stdout.flush()
        if cur==tot:
            sys.stdout.write("\r{}: [{}] 100% DONE!".format(line, "#"*bar))
            sys.stdout.flush()

localfile = sys.argv[2]
sd_name = os.path.split(localfile)[1]
ip_addr = sys.argv[1]

with open(localfile, 'r') as f:
    gcode = f.read()
body_buffer = BufferReader(gcode.encode(), progress)

# manager = urllib3.PoolManager()

# request = manager.request('POST', "http://{:s}/upload?X-Filename={:s}".format('192.168.1.109', name), headers={'Content-Type': 'application/octet-stream', 'Connection' : 'keep-alive'}, body=gcode.encode())
# print("Request code: %s" % request.status)

r = requests.post("http://{:s}/upload?X-Filename={:s}".format(ip_addr, sd_name), data=body_buffer, headers={'Content-Type': 'application/octet-stream', 'Connection' : 'keep-alive'})
print('\nFile uploaded!')
printUploaded = True if input("Start printing? (y/n): ").lower().startswith('y') else False
if printUploaded:
    print("Connecting to {}:8080".format(ip_addr))
    socket = pysock.socket(pysock.AF_INET, pysock.SOCK_STREAM)
    try:
        socket.connect((ip_addr, 8080))
    except Exception as e:
        print(e)
        raise(e)
    socket.send(("M23 %s" %sd_name + "\r\n").encode())
    socket.send(("M24" + "\r\n").encode())
    print("Disconnecting from {}:8080".format(ip_addr))
    try:
        socket.shutdown(pysock.SHUT_RDWR)
        socket.close()
    except Exception as e:
        print(e)
        raise(e)
print("Have a nice day!")
time.sleep(5)
exit()

# request = manager.request('POST', "http://{:s}/upload?X-Filename={:s}".format('192.168.1.109', name), headers={'Content-Type': 'application/octet-stream', 'Connection' : 'keep-alive'}, body=body_buffer, )
# print("Request code: %s" % request.status)