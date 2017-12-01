#!/bin/bash
echo "Running..."
pkill -F /home/austin/Documents/schepbot/logs/pid2.pid
/usr/bin/python3.6 -u /home/austin/Documents/schepbot/telosbot.py -b >> /home/austin/Documents/schepbot/logs/log2.log 2>&1 &
echo $! > /home/austin/Documents/schepbot/logs/pid2.pid
