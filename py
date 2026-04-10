#!/usr/bin/env python3

# Lightweight wrapper so you can run `py <script>` inside this repo.
# This simply forwards arguments to the system's python3 executable.

import sys
import os

if __name__ == '__main__':
    os.execvp('python3', ['python3'] + sys.argv[1:])
