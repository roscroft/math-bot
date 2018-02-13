#!/bin/bash
echo "Running..."
pkill -F /home/austin/dev/math-bot/logs/pid_mathbot.pid
/usr/bin/python3.6 -u /home/austin/dev/math-bot/mathbot.py -b >> /home/austin/dev/math-bot/logs/mathbot.log 2>&1 &
echo $! > /home/austin/dev/math-bot/logs/pid_mathbot.pid
