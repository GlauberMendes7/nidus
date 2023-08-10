#!/bin/bash

export PYTHONDONTWRITEBYTECODE=1

python -m nidus --config=config.json node-0 &
python -m nidus --config=config.json node-1 &
python -m nidus --config=config.json node-2 &
python -m nidus --config=config.json node-3 &
python -m nidus --config=config.json node-4 &

python -m nidus --leader=localhost:12000 SET fruits apples 3
python -m nidus --leader=localhost:12000 SET fruits oranges 5

sleep 10
pkill -9 python
rm *.log
