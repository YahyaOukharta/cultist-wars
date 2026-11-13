#!/bin/sh
# sweep.sh BASE GAMES NODES "FLAGS1" "FLAGS2" ...   each variant of bot.cpp (-D flags) vs league bot BASE
base=$1; games=$2; nodes=$3; shift 3
for v in "$@"; do
  c++ -O3 -std=c++17 -march=native -DLOCAL $v -o build/variant_$$ bot.cpp || exit 1
  printf '%s  ' "$v"
  python3 tools/league.py match build/variant_$$ "$base" -g "$games" -n "$nodes" | sed 's/^build\/variant vs [^:]*: //'
done
