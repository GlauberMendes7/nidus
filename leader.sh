#!/bin/bash

if [ $(ssh ubuntu-lab@10.7.125.172 'if [ -f /home/ubuntu-lab/Downloads/nidus-EDRaft/leader_flag.txt ]; then echo 1; else echo 0; fi') == 1 ]; then echo "10.7.125.172:12000" > leader.txt; fi;
if [ $(ssh ubuntu-lab@10.7.125.138 'if [ -f /home/ubuntu-lab/Downloads/nidus-EDRaft/leader_flag.txt ]; then echo 1; else echo 0; fi') == 1 ]; then echo "10.7.125.138:13000" > leader.txt; fi;
if [ $(ssh ubuntu-lab@10.7.125.164 'if [ -f /home/ubuntu-lab/Downloads/nidus-EDRaft/leader_flag.txt ]; then echo 1; else echo 0; fi') == 1 ]; then echo "10.7.125.164:14000" > leader.txt; fi;
if [ $(ssh ubuntu-lab@10.7.125.179 'if [ -f /home/ubuntu-lab/Downloads/nidus-EDRaft/leader_flag.txt ]; then echo 1; else echo 0; fi') == 1 ]; then echo "10.7.125.179:15000" > leader.txt; fi;
if [ $(ssh ubuntu-lab@10.7.125.97 'if [ -f /home/ubuntu-lab/Downloads/nidus-EDRaft/leader_flag.txt ]; then echo 1; else echo 0; fi') == 1 ]; then echo "10.7.125.97:16000" > leader.txt; fi;
