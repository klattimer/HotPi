/* picolor - a unix socket service for changing fan speed on raspberry-pi's gpio.
 *
 * Copyright (c) 2012 Karl Lattimer.
 * Author: Karl Lattimer <karl@qdh.org.uk>
 *
 * Start in the background as a daemon, access the service by firing
 * data at the picolor socket
 *
 */

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <math.h>
#include <wiringPi.h>
#include <softPwm.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>

#define PIN_FAN 6

#define TRUE 1
#define FALSE 0

float target_speed;
float speed;
float rate;

#define SLOW_START 100
#define MIN_SPEED 70

int sock, msgsock;

int keeprunning = TRUE;

void intHandler(int dummy) {
    keeprunning = FALSE;
}

void update_speed() {
    int changed = FALSE;

    if (roundf(speed) > roundf(target_speed)) {
        speed = speed - rate;
        changed = TRUE;
    } else if (roundf(speed) < roundf(target_speed)) {
        speed = speed + rate;
        changed = TRUE;
    }

    if (changed) {
        int s = roundf(speed);
        softPwmWrite(PIN_FAN, s);
    }
}

void set_speed(float s) {
    if (s < MIN_SPEED) {
        s = MIN_SPEED;
    }
    if (s < SLOW_START) {
        set_speed(255);
        delay(5);
    }
    speed = s;
    target_speed = s;
    int is = round(s);
    softPwmWrite(PIN_FAN, is);
}

void set_target_speed(float s) {
    if (s < MIN_SPEED) {
        s = MIN_SPEED;
    }
    if (s < SLOW_START) {
        set_speed(255);
        delay(5);
    }
    rate = (speed - s) / 255.0f;
    if (rate < 0) rate = rate * -1.0f;
    target_speed = s;
}

void read_socket() {
    char buf[2];
    int s;
    int rval;
    msgsock = accept(sock, 0, 0);
    if (msgsock != -1) {
        while (1) {
            bzero(buf, sizeof(buf));
            rval = read(msgsock, buf, 2);
            if (rval < 0) {
                perror("pifand: Error reading stream message");
                break;
            } else if (rval == 0) {
                break;
            } else if (buf[0] != 0) {
                s = (int)buf[1];
                if (buf[0] == '\x42') {
                    set_target_speed(s);
                } else if (buf[0] == '\x68') {
                    buf[0] = (char)speed;
                    buf[1] = 0;
                    write(msgsock, buf, 2);
                } else {
                    set_speed(s);
                }
            }
        }
    }
    close(msgsock);
}

int main (int argc, char **argv) {
    if (wiringPiSetup () == -1) {
        fprintf (stdout, "oops: %s\n", strerror (errno)) ;
        return 1;
    }

    if (argc < 1) {
        fprintf(stdout, "Usage: pifand /path/to/socket");
    }

    softPwmCreate (PIN_FAN, 0, 255);
    struct sockaddr_un server;
    sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("pifand: Error opening stream socket");
        exit(1);
    }
    fcntl(sock, F_SETFL, O_NONBLOCK);
    server.sun_family = AF_UNIX;
    strcpy(server.sun_path, argv[1]);
    if (bind(sock, (struct sockaddr *) &server, sizeof(struct sockaddr_un))) {
        perror("pifand: Error binding stream socket");
        exit(1);
    }

    listen(sock, 5);

    // Catch kill signals and ctrl+c
    signal(SIGINT, intHandler);
    signal(SIGKILL, intHandler);
    signal(SIGHUP, intHandler);

    while (keeprunning) {
        read_socket();
        update_speed();
        delay(10);
    }

    set_speed(0);
    delay(10);
    close(sock);
    unlink(argv[1]);
    return 0;
}

