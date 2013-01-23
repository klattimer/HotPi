/* picolor - a unix socket client for changing fan speed on raspberry-pi's gpio.
 *
 * Copyright (c) 2012 Karl Lattimer.
 * Author: Karl Lattimer <karl@qdh.org.uk>
 *
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define TRUE 1
#define FALSE 0

void usage(char *error, char *binaryPath) {
    if (error) {
        printf ("Error: %s\n", error);
    }
    printf ("Usage: %s <socket> [options] <speed>\n", binaryPath);
    printf ("Options:\n");
    printf (" -i        Change speed immediately\n");
    printf ("<speed>    0-255\n");
    printf("Example: %s /var/run/pifan 255\n", binaryPath);
}

int main(int argc, char **argv) {
    int sock;
    struct sockaddr_un server;
    char buf[2];

    if (argc < 2) {
        usage("Too Few Arguments", argv[0]);
        return 1;
    }

    int instant = FALSE;

    int i = 2;
    for (i = 2; i < argc; i++) {
        if (strncmp(argv[i], "-i", 2) == 0) {
            instant = TRUE;
        }
    }

    if (instant) {
	    buf[0] = '\x32';
    } else {
	    buf[0] = '\x42';
    }
    int speed = atoi(argv[argc - 1]);
    if (speed > 255) {
        speed = 255;
    }
    buf[1] = speed;

    sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("opening stream socket");
        return 2;
    }

    server.sun_family = AF_UNIX;
    strcpy(server.sun_path, argv[1]);

    if (connect(sock, (struct sockaddr *) &server, sizeof(struct sockaddr_un)) < 0) {
        close(sock);
        perror("connecting stream socket");
        return 3;
    }

    if (write(sock, buf, sizeof(buf)) < 0)
        perror("writing on stream socket");

    close(sock);
    return 0;
}

