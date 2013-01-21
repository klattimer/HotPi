HotPi
=====

HotPi userland software and utilities

1. HotPi Fan & Color LED control software

There are two daemons, pifand and picolord which are started with
/etc/init/hotpi.conf via upstart. Once these daemons are running
they will be able to receive instructions via the client commands
picolor and pifan. 

There is a third daemon 'hotpi-daemon' which monitors the system 
and uses the LED for reporting and adjusts the fan speed according
to the thermal trigger values. 

The RGB LED will notify you of updates by pulsing orange, security updates by pulsing red,
the system is offline by blinking yellow, the system is overheating by flashing red/blue.

2. Real Time Clock (hwclock)

Included are two primitive scrips hwclock.conf and hwclock-save.conf 
which can be placed in /etc/init in place of the existing scripts. 

This should be enough to activate the real time clock.
