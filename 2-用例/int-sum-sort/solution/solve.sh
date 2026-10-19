#!/bin/bash
# Gold solution (executed by harbor's oracle agent to validate reward=1.0).
{
  awk '{ s += $1 } END { print s }' /app/input.txt
  awk 'END { print NR }' /app/input.txt
  sort -n /app/input.txt
} > /app/output.txt
