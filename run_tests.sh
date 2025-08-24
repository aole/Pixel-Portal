#!/bin/bash
# This script runs the test suite using xvfb to provide a virtual display.
xvfb-run -a python3 -m pytest
