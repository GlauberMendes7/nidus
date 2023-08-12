#!/bin/bash

ssh ubuntu-lab@10.7.125.172 'sudo nohup pkill -9 python &' &
ssh ubuntu-lab@10.7.125.138 'sudo nohup pkill -9 python &' &
ssh ubuntu-lab@10.7.125.164 'sudo nohup pkill -9 python &' &
ssh ubuntu-lab@10.7.125.179 'sudo nohup pkill -9 python &' &
ssh ubuntu-lab@10.7.125.97 'sudo nohup pkill -9 python &' &
