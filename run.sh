#!/bin/bash

export PYTHONDONTWRITEBYTECODE=1

python -m nidus --config=config_metric.json node-0 &
python -m nidus --config=config_metric.json node-1 &
python -m nidus --config=config_metric.json node-2 &
python -m nidus --config=config_metric.json node-3 &
python -m nidus --config=config_metric.json node-4 &

python inputs.py

sleep 10
pkill -9 python
rm *.log
