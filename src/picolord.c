/* picolor - a unix socket service for changing RGB lights on raspberry-pi's gpio.
 *
 * Copyright (c) 2012 Karl Lattimer.
 * Author: Karl Lattimer <karl@qdh.org.uk>
 *
 * Start in the background as a daemon, access the service by firing
 * data at the picolor socket
 */

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#include <stdlib.h>
#include <wiringPi.h>
#include <softPwm.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>

#define PIN_RED 4
#define PIN_GREEN 5
#define PIN_BLUE 3

#define RED_MIN 0
#define RED_MAX 255

#define GREEN_MIN 0
#define GREEN_MAX 255

#define BLUE_MIN 0
#define BLUE_MAX 255

#define TRUE 1
#define FALSE 0

float red;
float green;
float blue;

float target_red;
float target_green;
float target_blue;

float rate_red;
float rate_green;
float rate_blue;

int sock, msgsock;
int delay_time = 1;
int keeprunning = TRUE;

void intHandler(int dummy) {
    keeprunning = FALSE;
}

void update_color() {
    int changed = FALSE;
    if (roundf(red) > roundf(target_red)) {
        red = red - rate_red;
        changed = TRUE;
    } else if (roundf(red) < roundf(target_red)) {
        red = red + rate_red;
        changed = TRUE;
    }

    if (roundf(green) > roundf(target_green)) {
        green = green - rate_green;
        changed = TRUE;
    } else if (roundf(green) < roundf(target_green)) {
        green = green + rate_green;
        changed = TRUE;
    }

    if (roundf(blue) > roundf(target_blue)) {
        blue = blue - rate_blue;
        changed = TRUE;
    } else if (roundf(blue) < roundf(target_blue)) {
        blue = blue + rate_blue;
        changed = TRUE;
    }

    int r, g, b;
    r = (int)roundf(red);
    g = (int)roundf(green);
    b = (int)roundf(blue);
    // Set the color on the PWM
    if (changed) {
        printf("Current Color: %0f %0f %0f\n", red, green, blue);
    }
    softPwmWrite(PIN_RED, r);
    softPwmWrite(PIN_GREEN, g);
    softPwmWrite(PIN_BLUE, b);
}

void set_target_color(float r, float g, float b) {
    rate_red = (red - r) / 255.0f;
    if (rate_red < 0) rate_red = rate_red * -1.0f;

    rate_green = (green - g) / 255.0f;
    if (rate_green < 0) rate_green = rate_green * -1.0f;

    rate_blue = (blue - b) / 255.0f;
    if (rate_blue < 0) rate_blue = rate_blue * -1.0f;

    target_red = r;
    target_green = g;
    target_blue = b;
}

void set_color(float r, float g, float b) {
    red = r;
    target_red = r;
    green = g;
    target_green = g;
    blue = b;
    target_blue = b;

    int ir, ig, ib;
    ir = round(red);
    ig = round(green);
    ib = round(blue);
    softPwmWrite(PIN_RED, ir);
    softPwmWrite(PIN_GREEN, ig);
    softPwmWrite(PIN_BLUE, ib);
}

float scale_value(float v, float min, float max) {
    float r = (max - min) / 255.0f;
    v = v * r;
    v = v + min;
    return v;
}

void read_socket() {
    char buf[4];
    int r,g,b;
    int rval;
    msgsock = accept(sock, 0, 0);
    if (msgsock != -1) {
        while (1) {
            bzero(buf, sizeof(buf));
            rval = read(msgsock, buf, 4);
            if (rval < 0) {
                perror("reading stream message");
                break;
            } else if (rval == 0) {
                printf("Ending connection\n");
                break;
            } else if (buf[0] != 0) {
                r = (int)buf[1];
                g = (int)buf[2];
                b = (int)buf[3];
                // Scale the values between the min and max
                r = scale_value(r, RED_MIN, RED_MAX);
                g = scale_value(g, GREEN_MIN, GREEN_MAX);
                b = scale_value(b, BLUE_MIN, BLUE_MAX);

                if (buf[0] == '\x42') {
                    set_target_color(r,g,b);
                } else {
                    set_color(r,g,b);
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
        fprintf(stdout, "Usage: picolord /path/to/socket");
    }

    softPwmCreate (PIN_RED, RED_MIN, RED_MAX);
    softPwmCreate (PIN_GREEN, GREEN_MIN, GREEN_MAX);
    softPwmCreate (PIN_BLUE, BLUE_MIN, BLUE_MAX);
    struct sockaddr_un server;
    sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("opening stream socket");
        exit(1);
    }
    fcntl(sock, F_SETFL, O_NONBLOCK);
    server.sun_family = AF_UNIX;
    strcpy(server.sun_path, argv[1]);
    if (bind(sock, (struct sockaddr *) &server, sizeof(struct sockaddr_un))) {
        perror("binding stream socket");
        exit(1);
    }

    printf("Socket has name %s\n", server.sun_path);
    listen(sock, 5);

    // Catch kill signals and ctrl+c
    signal(SIGINT, intHandler);
    signal(SIGKILL, intHandler);
    signal(SIGHUP, intHandler);

    while (keeprunning) {
        read_socket();
        update_color();
        delay(delay_time);
    }

    set_color(0,0,0);
    close(sock);
    unlink(NAME);
    return 0;
}

