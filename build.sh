#!/bin/bash
pip install -r requirements.txt

# Install libclang on Linux
apt-get update -y
apt-get install -y libclang-dev clang g++

# Find where libclang.so was installed and print it
find /usr -name "libclang*.so*" 2>/dev/null