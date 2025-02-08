#!/bin/bash

cd /workspace/RVC1006Nvidia
runtime/python.exe infer-web.py --pycmd runtime/python.exe --port 7897 &
sleep 20

echo "✅ RVC is running on http://localhost:7897"
