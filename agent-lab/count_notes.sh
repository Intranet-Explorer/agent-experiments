#!/bin/bash

# Count files in notes/ directory
count=$(find notes/ -maxdepth 1 -type f | wc -l)
echo "$count"