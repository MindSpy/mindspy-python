
.PHONY: proto regs_pb2.py

all: clean mindspy/proto.py

clean:
	rm ./mindspy/proto.py || true

mindspy/proto.py:
	$(MAKE) -C proto proto.py
	mv proto/proto.py $@
