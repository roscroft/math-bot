#!/bin/bash
echo "Running..."
pkill -F /home/austin/Documents/mathbot/logs/pid.pid
/usr/bin/python3.6 -u /home/austin/Documents/mathbot/mathbot.py -a >> /home/austin/Documents/mathbot/logs/log.log 2>&1 &
echo $! > /home/austin/Documents/mathbot/logs/pid.pid
