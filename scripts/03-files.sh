#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
./run.sh --vfs vfs/files.xml --startup scripts/03-startup.txt
