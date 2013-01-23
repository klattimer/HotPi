#
# Makefile:
#	wiringPi - Wiring Compatable library for the Raspberry Pi
#	https://projects.drogon.net/wiring-pi
#
#	Copyright (c) 2012 Gordon Henderson
#################################################################################
# This file is part of wiringPi:
#	Wiring Compatable library for the Raspberry Pi
#
#    wiringPi is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    wiringPi is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with wiringPi.  If not, see <http://www.gnu.org/licenses/>.
#################################################################################


#DEBUG	= -g -O0
DEBUG	= -O3
CC	= gcc
INCLUDE	= -I/usr/local/include
CFLAGS	= $(DEBUG) -Wall $(INCLUDE)  -Winline -pipe -static
DESTDIR = /usr
PREFIX  = 
LDFLAGS	= -L/usr/local/lib
LIBS    = -lwiringPi

# Should not alter anything below this line
###############################################################################

SRC	=	picolord.c picolor.c pifand.c pifan.c
BINS	=	picolord picolor pifand pifan
OBJ     =       $(SRC:.c=.o)

all: picolor pifan picolord pifand

pifand:	pifand.o
	@echo [link]
	$(CC) -o $@ pifand.o $(LDFLAGS) $(LIBS) -lm -lpthread

pifan:	pifan.o
	@echo [link]
	$(CC) -o $@ pifan.o $(LDFLAGS) $(LIBS) -lm

picolord:	picolord.o
	@echo [link]
	$(CC) -o $@ picolord.o $(LDFLAGS) $(LIBS) -lm -lpthread

picolor:	picolor.o
	@echo [link]
	$(CC) -o $@ picolor.o $(LDFLAGS) $(LIBS) -lm

.c.o:
	@echo [CC] $<
	@$(CC) -c $(CFLAGS) $< -o $@

clean:
	rm -f $(OBJ) *~ core tags picolor picolord pifan pifand

tags:	$(SRC)
	@echo [ctags]
	@ctags $(SRC)

depend:
	makedepend -Y $(SRC)

uninstall:
	@rm -rf $(DESTDIR)$(PREFIX)/bin/picolor
	@rm -rf $(DESTDIR)$(PREFIX)/bin/picolord
	@rm -rf $(DESTDIR)$(PREFIX)/bin/pifan
	@rm -rf $(DESTDIR)$(PREFIX)/bin/pifand

install: all
	@install -m 0755 picolor                $(DESTDIR)$(PREFIX)/bin
	@install -m 0755 picolord               $(DESTDIR)$(PREFIX)/bin
	@install -m 0755 pifan                  $(DESTDIR)$(PREFIX)/bin
	@install -m 0755 pifan                  $(DESTDIR)$(PREFIX)/bin

# DO NOT DELETE
