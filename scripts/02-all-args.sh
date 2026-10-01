#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
./run.sh --vfs vfs/minimal.xml --startup scripts/02-startup.txt
