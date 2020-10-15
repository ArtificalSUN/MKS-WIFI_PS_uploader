#! /usr/bin/env python
#  -*- coding: utf-8 -*-
# author: Victor Shapovalov (@ArtificalSUN), 2020
# version: 0.2.1

import sys, os, io, time
import requests

try:
    import Tkinter as tk
    import Tkinter.filedialog as fldg
except ImportError:
    import tkinter as tk
    import tkinter.filedialog as fldg

import mks_ass_gui as gui
import mks_ass_gui_support as gui_support

import mks_tools

def set_entry_text(entry, text):
    entry.delete(0,tk.END)
    entry.insert(0,text)
    return

def get_IP():
    global IP_addr
    IP_addr = str(svar_IP.get())

def connection_Establish():
    global IP_addr, Port, ActiveRelay, Debug, svar_LocalFileName, currentPoll, pollingDelay
    get_IP()
    try:
        ActiveRelay = mks_tools.MKS_relay(IP_addr, Port, top.prg_UploadStatus, root.winfo_toplevel().title)
        # ActiveRelay.ExtBar['value'] = 0
        ActiveRelay.updateExtBar(0)
        ActiveRelay.debug = Debug
        ActiveRelay.printUploaded = bvar_PrintUploaded.get()
        ActiveRelay.relay_start()
        if Autopoll:
            root.update_idletasks()
            currentPoll = root.after(pollingDelay, relayPoll)
        # currentPoll = root.after_idle(relayPoll)
        ActiveRelay.retrieveSDfiles()
        # svar_LocalFileName.set(ActiveRelay.SDfiles[0])

        top.ent_IP['state']=tk.DISABLED
        top.btn_Connect['text'] = "Disconnect"
        top.lbl_Connection_state.configure(text = '''CONNECTED''', foreground="#008e00")
        top.btn_Connect['command'] = connection_Finalize
        root.winfo_toplevel().title("MKS ASS @ {}:{}".format(IP_addr, Port))
    except Exception as e:
        print(e)
        raise(e)

def connection_Finalize():
    global IP_addr, Port, ActiveRelay, svar_LocalFileName
    try:
        ActiveRelay.relay_stop()
        del ActiveRelay
        ActiveRelay = None
        if currentPoll:
            root.after_cancel(currentPoll)
            del currentPoll
            currentPoll = None
        svar_LocalFileName.set('connection closed')

        top.ent_IP['state'] = tk.NORMAL
        top.btn_Connect["text"] = "Connect"
        top.lbl_Connection_state.configure(text = '''NOT CONNECTED''', foreground = "#ff0000")
        top.btn_Connect['command'] = connection_Establish
    except Exception as e:
        print(e)

def relayPoll():
    global ActiveRelay, pollingDelay
    root.winfo_toplevel().title("MKS ASS @ {}:{} (checking ActiveRelay)".format(IP_addr, Port))
    if isinstance(ActiveRelay, mks_tools.MKS_relay) and ActiveRelay.isConnected:
        root.winfo_toplevel().title("MKS ASS @ {}:{} (polling from ActiveRelay)".format(IP_addr, Port))
        ActiveRelay.readFromRelay()
        root.winfo_toplevel().title("MKS ASS @ {}:{} (updating idle tasks)".format(IP_addr, Port))
        root.update_idletasks()
        # root.after_idle(relayPoll)
        root.winfo_toplevel().title("MKS ASS @ {}:{} (rescheduling polling)".format(IP_addr, Port))
        if Autopoll: root.after(pollingDelay, relayPoll)
        root.winfo_toplevel().title("MKS ASS @ {}:{}".format(IP_addr, Port))


def get_Local_File():
    global LocalFileName, svar_LocalFileName, svar_NewFileName
    LocalFileName = fldg.askopenfilename()
    svar_LocalFileName.set(LocalFileName)
    svar_NewFileName.set(os.path.split(LocalFileName)[1])

def get_printUploaded():
    global ActiveRelay, bvar_PrintUploaded
    if isinstance(ActiveRelay, mks_tools.MKS_relay) and ActiveRelay.isConnected:
        ActiveRelay.printUploaded = bvar_PrintUploaded.get()

def upload_File():
    global LocalFileName, RemoteFileName, ActiveRelay, currentPoll, pollingDelay, Autopoll
    if currentPoll:
        root.after_cancel(currentPoll)
        del currentPoll
        currentPoll = None
        root.winfo_toplevel().title("MKS ASS @ {}:{} (polling paused, uploading file)".format(IP_addr, Port))

    LocalFileName = str(svar_LocalFileName.get())
    ActiveRelay.local_filename = LocalFileName
    RemoteFileName = svar_NewFileName.get()
    ActiveRelay.sd_filename = RemoteFileName
    if Debug: print("Uploading {} to {} as {}".format(LocalFileName, IP_addr, ActiveRelay.sd_filename))
    try:
        # ActiveRelay.upload()
        with open(LocalFileName, 'r') as f:
            gcode = f.read()
        body_buffer = mks_tools.BufferReader(gcode.encode(), upload_progress)
        r = requests.post("http://{:s}/upload?X-Filename={:s}".format(IP_addr, RemoteFileName), data=body_buffer, headers={'Content-Type': 'application/octet-stream', 'Connection' : 'keep-alive'})
        print("Request code: %s" % r.text)
        if ActiveRelay.printUploaded:
            ActiveRelay.printFile()
    except Exception as e:
        print(e)
        raise(e)

    if ActiveRelay.isConnected:
        root.update_idletasks()
        currentPoll = root.after(pollingDelay, relayPoll)

def upload_progress(size, progress):
    if size > 0:
        prog_perc = progress*100/size
        print("Streaming bytes {0} / {1} ({2:.2f}%)".format(progress, size, prog_perc))
        top.prg_UploadStatus['value'] = int(prog_perc)
        top.lbl_UploadStatus['text'] = "{0} / {1} ({2:.2f}%)".format(progress, size, prog_perc)
        # root.update_idletasks()

root = tk.Tk()
gui_support.set_Tk_var()
top = gui.Main(root)
gui_support.init(root, top)

svar_LocalFileName = tk.StringVar()
top.ent_LocalFile.configure(textvariable = svar_LocalFileName)
svar_NewFileName = tk.StringVar()
top.ent_NewName.configure(textvariable = svar_NewFileName)
svar_IP = tk.StringVar()
top.ent_IP.configure(textvariable = svar_IP)
bvar_PrintUploaded = tk.BooleanVar()
top.chk_PrintUploaded.configure(variable = bvar_PrintUploaded)

top.btn_FileSel.configure(command = get_Local_File)
top.btn_Upload.configure(command = upload_File)
top.btn_Connect.configure(command = connection_Establish)
top.chk_PrintUploaded.configure(command = get_printUploaded)

Debug = True
Autopoll = True
ActiveRelay = None
currentPoll = None
pollingDelay = 750
IP_addr = ""
Port = 8080
LocalFileName = ""
RemoteFileName = ""

if __name__ == '__main__':
    root.mainloop()