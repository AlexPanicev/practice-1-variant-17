#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
./run.sh --vfs vfs/deep.xml --startup scripts/04-startup.txt
