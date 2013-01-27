#!/bin/bash

# Build wiringPi
cd wiringPi/wiringPi
make
make static
cd ../../

# Build picolor & pifan utilities
cd src
make
cd ..

