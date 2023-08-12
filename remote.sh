#!/bin/bash

sudo su

echo "SUDO!"

cd /home/ubuntu-lab/nidus

rm -rf nidus_log

sleep 0

python -m nidus --config=config.json node-0
