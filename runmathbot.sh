#!/bin/bash
echo "Running..."
pkill -F /home/austin/Documents/math-bot/logs/pid_mathbot.pid
/usr/bin/python3.6 -u /home/austin/Documents/math-bot/mathbot.py -b >> /home/austin/Documents/math-bot/logs/mathbot.log 2>&1 &
echo $! > /home/austin/Documents/math-bot/logs/pid_mathbot.pid
