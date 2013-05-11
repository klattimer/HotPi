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
 LED_PATTERN_MESSAGES,
 LED_PATTERN_STATIC,
 LED_PATTERN_OFF) = (32,16,8,4,2,1,0)

URL_REFERENCES = ["www.google.com", "www.yahoo.com", "www.bing.com", "www.facebook.com"] # Places to check for an internet connection

class HotPiDaemon:
    def __init__(self):
        self.readConfig()
        self._default_pattern = eval(self._conf['DEFAULT_LED_PATTERN'])
        self._default_color = self.parseColor(self._conf['DEFAULT_STATIC_COLOR'])
        if self._default_color == [0,0,0]: self._default_color = self.getColor()
        
        self._current_pattern_index = 0
        self._check_interval_updates = 20 * 60
        self._check_interval_cpu = 60
        self._check_interval_online = 15 * 60
        self._last_check_time_updates = 0
        self._last_check_time_cpu = 0
        self._last_check_time_online = 0
        self._no_of_messages = 0
        self._message_gap = ((10,0,20), 200, False) # gap between message blinks

        self._patterns = {}
        self._patterns[LED_PATTERN_OVERHEAT] = [((255,0,0), 100, True), ((0,0,255), 100, True)]
        self._patterns[LED_PATTERN_SECURITY] = [((255,30,0), 1000, False), ((255,0,20), 1000, False)]
        self._patterns[LED_PATTERN_UPDATES] = [((140,200,0), 1000, False), ((40,100,255), 1000, False)]
        self._patterns[LED_PATTERN_OFFLINE] = [((70,140,0), 500, True), ((0,0,0), 500, True)]
        self._patterns[LED_PATTERN_MESSAGES] = [((20,0,40), 100, False), ((20,0,200), 180, False)]
        if self._default_color != [0,0,0]:
            self._patterns[LED_PATTERN_STATIC] = [((self._default_color[0], self._default_color[1], self._default_color[2]), 10000, False)]
        self._patterns[LED_PATTERN_OFF] = [((0,0,0),10000,False)]

        self._active_patterns = self._default_pattern

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

        self._running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGKILL, self._signal_handler)
        signal.signal(signal.SIGHUP, self._signal_handler)
        
        last_top = None
        while self._running:
            ct = time.time()
            if ct - self._last_check_time_updates >= self._check_interval_updates:
                self.checkUpdates()
            if ct - self._last_check_time_cpu >= self._check_interval_cpu:
                self.checkCPU()
            if ct - self._last_check_time_online >= self._check_interval_online:
                self.checkOnline()
            top_pattern = self.topPattern()
            if top_pattern == last_top: continue
            if top_pattern == self._patterns[LED_PATTERN_STATIC]:
                # Save the colour in case it was changed outside hotpi-daemon
                self._default_color = self.getColor()
                
            last_top = top_pattern
            (color, duration, instant) = top_pattern[self._current_pattern_index]
            self.setColor(color, duration, instant)
            self._current_pattern_index = self._current_pattern_index + 1
            if self._current_pattern_index > len(top_pattern) - 1:
                self._current_pattern_index = 0

    def _signal_handler(self, signal, frame):
        self._running = False
        
    def readConfig(self):
        if not os.path.isfile(CONF_FILE):
            print "HotPiDaemon: Config file: \"%s\" does not exist" % CONF_FILE
            sys.exit(1)

        config_file= open(CONF_FILE)
        config = {  "COLOR_SOCKET" : None,
                    "FAN_SOCKET": None,
                    "TEMP_FILE": "/sys/class/thermal/thermal_zone0/temp",
                    "TEMP_MULTIPLIER": "1000",
                    "CPUSPEED_FILE": "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq",
                    "CPUSPEED_MULTIPLIER":"1000",
                    "CPUSPEED_LOW" : "600",
                    "CPUSPEED_HIGH" : "1000",
                    "CPUSPEED_LOW_FANSPEED" : "40",
                    "CPUSPEED_HIGH_FANSPEED" : "150",
                    "TEMP_LOW" : "40",
                    "TEMP_LOW_FANSPEED" : "90",
                    "TEMP_HIGH" : "75",
                    "TEMP_HIGH_FANSPEED" : "255",
                    "TEMP_ALARM" : "85",
                    "DEFAULT_LED_PATTERN" : "LED_PATTERN_OFF",
                    "DEFAULT_STATIC_COLOR" : "#FF00D4" }

        for line in config_file:
            line = line.strip()
            if line and line[0] is not "#" and line[-1] is not "=":
                var,val = line.rsplit("=",1)
                config[var.strip()] = val.strip()
        self._conf = config

    def parseColor(self,color):
        if len(color) < 6: return [0,0,0]
        color = color[len(color) - 6:] # last 6 chars of the string
        split = (color[0:2], color[2:4], color[4:6])
        return [int(x, 16) for x in split]

    def getColor( self ):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._conf['COLOR_SOCKET'])
        sock.send("\x68");
        data = sock.recv(4)
        sock.close()
        r = int(data[0])
        g = int(data[1])
        b = int(data[2])
        return [r,g,b]

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
        if self._active_patterns & LED_PATTERN_MESSAGES == LED_PATTERN_MESSAGES:
            if self._no_of_messages > 0:
                p = []
                for i in range(self._no_of_messages):
                    p.extend(self._patterns[LED_PATTERN_MESSAGES])
                p.append(self._message_gap)
                return p
        if self._active_patterns & LED_PATTERN_STATIC == LED_PATTERN_STATIC:
            return self._patterns[LED_PATTERN_STATIC]
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

    def getCPUSpeed(self):
        speed = 0
        f = open(self._conf['CPUSPEED_FILE'], "r")
        data = f.read()
        f.close()
        data = data.strip()
        speed = float(int(data)) / float(int(self._conf['CPUSPEED_MULTIPLIER']))
        return speed

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
        if speed > 255: speed = 255
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

    def checkMessages(self):
        # TODO: how could/should we get no of messages waiting and mark/unmark messages? 
        self._no_of_messages = 0

    def calculateFanSpeed(self, low_value, low_speed, high_value, high_speed, value):
        if value < low_value: return 0
        if value > high_value: return 255
        v = float(value - low_value) / float(high_value - low_value)
        s = (v * float(high_speed - low_speed)) + low_speed
        return s

    def checkCPU(self):
        t = self.getTemp()
        s = self.getCPUSpeed()
        
        fanspeed = self.calculateFanSpeed(int(self._conf['TEMP_LOW']), int(self._conf['TEMP_LOW_FANSPEED']),
                                          int(self._conf['TEMP_HIGH']), int(self._conf['TEMP_HIGH_FANSPEED']),
                                          t) +
                   self.calculateFanSpeed(int(self._conf['CPUSPEED_LOW']), int(self._conf['CPUSPEED_LOW_FANSPEED']),
                                          int(self._conf['CPUSPEED_HIGH']), int(self._conf['CPUSPEED_HIGH_FANSPEED']),
                                          s)
        self.setFanSpeed(fanspeed)
        if t >= int(self._conf['TEMP_ALARM']):
            self.pushPattern(LED_PATTERN_OVERHEAT)
        else:
            self.popPattern(LED_PATTERN_OVERHEAT)
            

if __name__ == "__main__":
    h = HotPiDaemon()
    h.setColor((0,0,0), 0, False)