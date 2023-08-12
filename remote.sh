#!/bin/bash

# cd /home/ftgo/repo/ftgo/nidus-EDRaft
cd /home/ubuntu-lab/Downloads/nidus-EDRaft

rm -rf nidus_log


sleep ${1}

# sudo /home/ftgo/repo/ftgo/nidus-EDRaft/.venv/bin/python -m nidus --config=${2} ${3} 1>remote.log 2>&1
sudo /home/ubuntu-lab/Downloads/nidus-EDRaft/.venv/bin/python -m nidus --config=${2} ${3} 1>remote.log 2>&1
