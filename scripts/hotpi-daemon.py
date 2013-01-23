#!/usr/bin/env python

# Missing features
# * message indicator, fades in and out if messages are waiting *somewhere*
#      indicates how many messages by how many times it flashes.
# * static - user defined colour - as from config file, or from the picolord
# * blink for LIRC? It's slightly outside of the design of this at present
#      but potentially possible with pylirc.

import socket
import signal
import time
import sys
import random
import os
import urllib2
import subprocess

CONF_FILE = "/etc/default/hotpi"

(LED_PATTERN_OVERHEAT,
 LED_PATTERN_OFFLINE,
 LED_PATTERN_SECURITY,
 LED_PATTERN_UPDATES,
 LED_PATTERN_OFF) = (8,4,2,1,0)

URL_REFERENCES = ["www.google.com"] # Places to check for an internet connection

class HotPiDaemon:
    def __init__(self):
        self.readConfig()
        self._running = True
        self._default_pattern = eval(self._conf['DEFAULT_LED_PATTERN'])
        self._current_pattern_index = 0
        self._check_interval_updates = 20 * 60
        self._check_interval_temp = 60
        self._check_interval_online = 15 * 60
        self._last_check_time_updates = 0
        self._last_check_time_temp = 0
        self._last_check_time_online = 0

        self._patterns = {}
        self._patterns[LED_PATTERN_OVERHEAT] = [((255,0,0), 100, True), ((0,0,255), 100, True)]
        self._patterns[LED_PATTERN_SECURITY] = [((255,30,0), 1000, False), ((255,0,20), 1000, False)]
        self._patterns[LED_PATTERN_UPDATES] = [((140,200,0), 1000, False), ((40,100,255), 1000, False)]
        self._patterns[LED_PATTERN_OFFLINE] = [((70,140,0), 500, True), ((0,0,0), 500, True)]
        self._patterns[LED_PATTERN_OFF] = [((0,0,0),0,False)]

        self._active_patterns = self._default_pattern

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGKILL, self._signal_handler)
        signal.signal(signal.SIGHUP, self._signal_handler)

        # Check sockets exist
        self._enable_fan = True
        if not os.path.isfile(self._conf['FAN_SOCKET']):
            self._enable_fan = False

        self._enable_led = True
        if not os.path.isfile(self._conf['COLOR_SOCKET']):
            self._enable_led = False

        self._speed = self.getFanSpeed()

        (color, duration, instant) = self._patterns[self._default_pattern][self._current_pattern_index]
        self.setColor(color, duration, instant)

        if not self._enable_fan and not self._enable_led:
            print "HotPiDaemon: Fan and LED are disabled, nothing do do :("
            sys.exit(1)

        while self._running:
            ct = time.time()
            if ct - self._last_check_time_updates >= self._check_interval_updates:
                self.checkUpdates()
            if ct - self._last_check_time_temp >= self._check_interval_temp:
                self.checkTemp()
            if ct - self._last_check_time_online >= self._check_interval_online:
                self.checkOnline()
            top_pattern = self.topPattern()
            (color, duration, instant) = top_pattern[self._current_pattern_index]
            self.setColor(color, duration, instant)
            self._current_pattern_index = self._current_pattern_index + 1
            if self._current_pattern_index > len(top_pattern) - 1:
                self._current_pattern_index = 0

    def readConfig(self):
        if not os.path.isfile(CONF_FILE):
            print "HotPiDaemon: Config file: \"%s\" does not exist" % CONF_FILE
            sys.exit(1)

        config_file= open(CONF_FILE)
        config = {  "COLOR_SOCKET" : None,
                    "FAN_SOCKET": None,
                    "TEMP_FILE": "/sys/class/thermal/thermal_zone0/temp",
                    "TRIGGER_LOW_TEMP" : "40",
                    "TRIGGER_LOW_SPEED" : "90",
                    "TRIGGER_MEDIUM_TEMP" : "60",
                    "TRIGGER_MEDIUM_SPEED" : "150",
                    "TRIGGER_HIGH_TEMP" : "75",
                    "TRIGGER_HIGH_SPEED" : "255",
                    "DEFAULT_LED_PATTERN" : "LED_PATTERN_OFF" }

        for line in config_file:
            line = line.strip()
            if line and line[0] is not "#" and line[-1] is not "=":
                var,val = line.rsplit("=",1)
                config[var.strip()] = val.strip()
        self._conf = config

    def parseColor(self,color):
        color = color[len(color) - 6:] # last 6 chars of the string
        split = (color[0:2], color[2:4], color[4:6])
        return [int(x, 16) for x in split]

    def _signal_handler(self, signal, frame):
        self._running = False

    def setColor(self, color, duration=255, instant=False):
        (r,g,b) = color
        delay = int(float(duration) / 255.0)
        if delay > 255: delay = 255
        if instant: i = 0x32
        else: i = 0x42
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['COLOR_SOCKET'])
        sock.send("%2x%2x%2x%2x%2x" % (i,r,g,b,delay))
        sock.close()
        time.sleep(duration/1000.0)

    def topPattern(self):
        if self._active_patterns & LED_PATTERN_OVERHEAT == LED_PATTERN_OVERHEAT:
            return self._patterns[LED_PATTERN_OVERHEAT]
        if self._active_patterns & LED_PATTERN_OFFLINE == LED_PATTERN_OFFLINE:
            return self._patterns[LED_PATTERN_OFFLINE]
        if self._active_patterns & LED_PATTERN_SECURITY == LED_PATTERN_SECURITY:
            return self._patterns[LED_PATTERN_SECURITY]
        if self._active_patterns & LED_PATTERN_UPDATES == LED_PATTERN_UPDATES:
            return self._patterns[LED_PATTERN_UPDATES]
        return self._patterns[LED_PATTERN_OFF]

    def pushPattern(self, pattern):
        self._active_patterns = self._active_patterns | pattern

    def popPattern(self, pattern):
        pattern = ~pattern
        self._active_patterns = self._active_patterns & pattern

    def getTemp(self):
        temp = 0
        f = open(self._conf['TEMP_FILE'], "r")
        data = f.read()
        f.close()
        data = data.strip()
        temp = float(int(data)) / float(int(self._conf['TEMP_MULTIPLIER']))
        return temp

    def getFanSpeed(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['FAN_SOCKET'])
        sock.send("\x68");
        data = sock.recv(2)
        sock.close()
        return int(data)

    def setFanSpeed(self, speed):
        if speed == self._speed: return
        self._speed = speed
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['FAN_SOCKET'])
        sock.send("\x32%2x" % speed)
        sock.close()

    def checkOnline(self):
        reference = URL_REFERENCES[random.randint(0, len(URL_REFERENCES) - 1)]
        try:
            urllib2.urlopen(reference, timeout=2)
            self.popPattern(LED_PATTERN_OFFLINE)
        except urllib2.URLError:
            self.pushPattern(LED_PATTERN_OFFLINE)

    def checkUpdates(self):
        if os.path.isfile("/usr/lib/update-notifier/apt-check"):
            try:
                r = subprocess.check_output("/usr/lib/update-notifier/apt-check", stderr=subprocess.STDOUT)
                (u,s) = r.split(";")
                if int(s) > 0:
                    self.pushPattern(LED_PATTERN_SECURITY)
                elif int(u) > 0:
                    self.pushPattern(LED_PATTERN_UPDATES)
                else:
                    self.popPattern(LED_PATTERN_UPDATES)
                    self.popPattern(LED_PATTERN_SECURITY)
            except:
                self.popPattern(LED_PATTERN_UPDATES)
                self.popPattern(LED_PATTERN_SECURITY)

    def checkTemp(self):
        t = self.getTemp()
        if t < int(self._conf['TRIGGER_LOW_TEMP']):
            self.setFanSpeed(0)
            self.popPattern(LED_PATTERN_OVERHEAT)
        elif t >= int(self._conf['TRIGGER_LOW_TEMP']):
            self.setFanSpeed(int(self._conf['TRIGGER_LOW_SPEED']))
            self.popPattern(LED_PATTERN_OVERHEAT)
        elif t >= int(self._conf['TRIGGER_MEDIUM_TEMP']):
            self.setFanSpeed(int(self._conf['TRIGGER_MEDIUM_SPEED']))
            self.popPattern(LED_PATTERN_OVERHEAT)
        elif t >= int(self._conf['TRIGGER_HIGH_TEMP']):
            self.setFanSpeed(int(self._conf['TRIGGER_HIGH_SPEED']))
            self.pushPattern(LED_PATTERN_OVERHEAT)

if __name__ == "__main__":
    h = HotPiDaemon()
    h.setColor((0,0,0), 0, False)