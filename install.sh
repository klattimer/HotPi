#!/bin/bash

# Install wiringPi
cd wiringPi/wiringPi
make install
make install-static
cd ../../

# Install picolor & pifan utilities
cd src
make install 
cd ..

# Install scripts & config files
install -m 0644 conf/hotpi /etc/default/
install -m 0644 scripts/hotpi.conf /etc/init
install -m 0644 scripts/hwclock.conf /etc/init
install -m 0644 scripts/hwclock-save.conf /etc/init
install -m 0644 scripts/hotpi-daemon.py /usr/bin/hotpi-daemon
