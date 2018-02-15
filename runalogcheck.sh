#!/bin/bash
echo "Running..."
/usr/bin/python3.6 -u /home/austin/dev/math-bot/alog_check.py -c >> /home/austin/dev/math-bot/logs/cap_check.log 2>&1 &
