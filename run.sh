#! /bin/bash
#Run main.py, restarting it if exit code == 89
while true; do
    python3 main.py
    if [ $? -ne 89 ]; then
        break
    fi
done