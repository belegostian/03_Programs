#!/bin/bash

./clientA.py &
./clientB.py &

wait -n
exit $?