# Local builds. The submission itself is produced by tools/pack.py.
CXX      ?= c++
CXXFLAGS ?= -O3 -std=c++17 -march=native

all: build/bot build/referee

build/bot: bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -o $@ $<

build/referee: tools/referee.cpp bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -o $@ $<

pack:
	python3 tools/pack.py -o out/submission.cpp

clean:
	rm -rf build out

.PHONY: all pack clean
