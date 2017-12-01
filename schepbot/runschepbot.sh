#!/bin/bash
echo "Running..."
pkill -F /home/austin/Documents/schepbot/logs/pid.pid
/usr/bin/python3.6 -u /home/austin/Documents/schepbot/schepbot.py -c >> /home/austin/Documents/schepbot/logs/log.log 2>&1 &
echo $! > /home/austin/Documents/schepbot/logs/pid.pid
