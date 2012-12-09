#!/usr/bin/env python
# pifan-thermal

import socket
import signal
import time
import sys

CONF_FILE = "/etc/default/pifan"

def readConfig(filename):
    config_file= open(filename)
    config = {}

    for line in config_file:
        line = line.strip()
        if line and line[0] is not "#" and line[-1] is not "=":
            var,val = line.rsplit("=",1)
            config[var.strip()] = val.strip()
    return config

class MonitorTemp:
    def __init__(self, conf):
        self._conf = conf
        self._running = True

        self._speed = self.getFanSpeed()

        signal.signal(signal.SIGINT, self._signal_handler)
        #signal.signal(signal.SIGKILL, self._signal_handler)

        while self._running:
            self.checkTemp()
            time.sleep(60)

    def _signal_handler(self, signal, frame):
        self._running = False

    def getTemp(self):
        temp = 0
        f = open(self._conf['TEMP_FILE'], "r")
        data = f.read()
        f.close()
        data = data.strip()
        temp = float(int(data)) / float(int(self._conf['TEMP_MULTIPLIER']))
        print temp
        return temp

    def getFanSpeed(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['SOCKET'])
        sock.send("\x68");
        data = sock.recv(2)
        sock.close()
        return 0

    def setFanSpeed(self, speed):
        if speed == self._speed: return
        self._speed = speed
        print "Setting Speed to %d" % speed
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['SOCKET'])
        sock.send("\x32%2x" % speed);
        sock.close()

    def checkTemp(self):
        t = self.getTemp()
        print self._conf['TRIGGER_LOW_TEMP']
        print int(self._conf['TRIGGER_LOW_TEMP'])
        if t < int(self._conf['TRIGGER_LOW_TEMP']):
            print "a"
            self.setFanSpeed(0)
        elif t >= int(self._conf['TRIGGER_LOW_TEMP']):
            print "b"
            self.setFanSpeed(int(self._conf['TRIGGER_LOW_SPEED']))
        elif t >= int(self._conf['TRIGGER_MEDIUM_TEMP']):
            print "c"
            self.setFanSpeed(int(self._conf['TRIGGER_MEDIUM_SPEED']))
        elif t >= int(self._conf['TRIGGER_HIGH_TEMP']):
            print "d"
            self.setFanSpeed(int(self._conf['TRIGGER_HIGH_SPEED']))

if __name__ == "__main__":
    conf = readConfig(CONF_FILE)
    MonitorTemp(conf)
