
.PHONY: proto regs_pb2.py

all: clean proto regs_pb2.py

clean:
	rm regs_pb2.py || true

proto:
	$(MAKE) -C $@

regs_pb2.py: proto
	mv proto/regs_pb2.py ./mindspy/
