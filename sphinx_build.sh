#!/bin/bash

# Navigate to docs directory
cd docs

# Remove old docs
rm -rf build/*

# Build HTML documentation
make html

# Open docs
xdg-open build/html/index.html
