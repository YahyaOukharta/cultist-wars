# Local builds. The submission itself is produced by tools/pack.py.
CXX      ?= c++
CXXFLAGS ?= -O3 -std=c++17 -march=native

# build/bot and build/referee use the handcrafted evaluation. build/gen (self-play data) and
# build/referee_lab (search labels for arena positions) read a 64-hidden net from CW_NET.
all: build/bot build/referee build/gen build/referee_lab

build/bot: bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -o $@ $<

build/referee: tools/referee.cpp bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -o $@ $<

build/gen: bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -DNN_H=64 -o $@ $<

build/referee_lab: tools/referee.cpp bot.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -DLOCAL -DNN_H=64 -o $@ $<

# the live submission (v2.8a): bot.cpp defaults + the n12a net
pack:
	python3 tools/pack.py -n tools/nets/n12a.bin -H 64 -o out/submission.cpp

clean:
	rm -rf build out

.PHONY: all pack clean
