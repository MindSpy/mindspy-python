#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [ 'CodedStream', 'CodedSerialStream', 'CodedSubprocessStream' ]

from threading import Thread, Event
from Queue import Queue, Full, Empty
from subprocess import Popen, PIPE
from serial import Serial
import logging

# FIXME internal APIS
from google.protobuf.internal.encoder import _EncodeVarint
from google.protobuf.internal.decoder import _DecodeVarint

logger = logging.getLogger(__name__)

def _encode_varint(i):
    """Encode integer as varint
    """
    buff = bytearray()
    _EncodeVarint(buff.append, i)
    return buff

def _decode_varint(serial):
    """Decode varint as integer
    """
    try:
        i,count =_DecodeVarint(serial,0)
        return i, serial[count:]
    except IndexError:
        return None, serial

class CodedThread(Thread):
    """
    """
    def __init__(self, queue, stream, MsgClass, stop):
        Thread.__init__(self)
        self.daemon = True
        self._queue = queue
        self._stream = stream
        self._MsgClass = MsgClass
        self._stop = stop
        # TODO handle stream reset condition
        # * if one side resets the communication - it should send stream reset message
        # * this message is intercept by other side
        # * the other one replies with same message - communication is now reset (buffers flushed etc.)
        # * stream reset is decision of either sides - e.g. stream out of sync
        # * each side should handle it autonomously
        self._reset = None

class InThread(CodedThread):
    def run(self):
        try:
            #print 'starting in'
            serial = ''
            size = None
            while not self._stop.is_set():
                # this will block here
                serial += self._stream.read(1)
                if size is None:
                    # intercept size of the message
                    size, serial = _decode_varint(serial)
                else:
                    # intercept 'size' number of bytes
                    if len(serial) >= size:
                        # split the incomming token
                        token = serial[:size]
                        # generate response message

                        try:
                            message = self._MsgClass()
                            message.MergeFromString(token)
                        except Exception:
                            ## TODO check for stream reset message and reset the state
                            continue

                        # advance the state
                        serial = serial[size:]
                        size = None

                        try:
                            self._queue.put(message, timeout=1.)
                        except Full:
                            print 'Queue full. Current message discarded.'
                            continue # => discard current message

        finally:
            pass #print 'exiting in'


class OutThread(CodedThread):
    def run(self):
        try:
            #print 'starting out'
            while not self._stop.is_set():
                try:
                    message = self._queue.get(timeout=1.)
                    buff = message.SerializeToString()
                    self._stream.write(_encode_varint(len(buff))+buff)
                except Empty:
                    continue
        finally:
            pass #print 'exiting out'

class CodedStream:
    def __init__(self, istream, ostream, RequestClass, ResponseClass):
        self._iqueue = Queue(1000)
        self._oqueue = Queue(1000)
        self._stop = Event()
        self._ReqClass = RequestClass
        self._ResClass = ResponseClass
        self._ithread = InThread(self._iqueue, istream, self._ResClass, self._stop)
        self._othread = OutThread(self._oqueue, ostream, self._ReqClass, self._stop)
        self._ithread.start()
        self._othread.start()
    def __del__(self):
        self._stop.set()
        self._othread.join()
        self._ithread.join(timeout=1.0)
    def get(self, block=True, timeout=None):
        message = self._iqueue.get(block, timeout)
        return message
    def put(self, message, block=True, timeout=None):
        if not isinstance(message, self._ReqClass):
            raise TypeError('Expected message of type "%s".' % self._ReqClass.__name__)
        return self._oqueue.put(message, block, timeout)

class CodedSubprocessStream(CodedStream):
    def __init__(self, args, RequestClass, ResponseClass):
        self._p = Popen(args, stdin=PIPE, stdout=PIPE)
        CodedStream.__init__(self, self._p.stdout, self._p.stdin, RequestClass, ResponseClass)
    def __del__(self):
        self._p.kill()

class CodedSerialStream(CodedStream):
    def __init__(self, dev, baud, timeout, RequestClass, ResponseClass):
        self._s = Serial(dev, baud, timeout=timeout)
        CodedStream.__init__(self, self._s, self._s, RequestClass, ResponseClass)
    def __del__(self):
        self._s.close()