import logging
logger = logging.getLogger(__name__)

class MindSpy(object):
    def __init__(self, stream):
        from itertools import count
        from Queue import Queue
        from threading import Thread
        self._reqid = count()
        self._stream = stream
        self._readbuffer = ''
        self._queue = Queue()
        class T(Thread):
            def __init__(self, target):
                super(T, self).__init__(target=target)
                self.daemon = True
                self.name = 'messagereader'
        self._t = T( self._read)
        #self._t.start()

    @staticmethod
    def _timestamp():
        from time import time
        return int(time()*1e6)  #in micros

    @staticmethod
    def _encode_varint(i):
        from google.protobuf.internal.encoder import _EncodeVarint
        buff = bytearray()
        _EncodeVarint(buff.append, i)
        return buff

    @staticmethod
    def _decode_varint(s):
        from google.protobuf.internal.decoder import _DecodeVarint
        i,t = _DecodeVarint(s,0)
        return i,t

    @staticmethod
    def _serialize_delimited(message):
        buff = message.SerializeToString()
        return MindSpy._encode_varint(len(buff)) +  buff

    @staticmethod
    def _deserialize_delimited(serialized, Message):
        try:
            count, token = MindSpy._decode_varint(serialized)
        except IndexError:
            return None, serialized
        if token+count >= len(serialized):
            return None, serialized
        rest = serialized[token:token+count]
        msg = Message()
        msg.MergeFromString(rest)
        return msg, serialized[token+count:]

    def _req_init(self, **kw):
        from .regs_pb2 import Request
        req = Request()
        req.timestamp = self._timestamp()
        req.reqid = self._reqid.next()
        for k,v in kw.items():
            setattr(req, k, v)
        return req

    def _req_echo(self):
        from .regs_pb2 import Request
        return self._req_init(action = Request.ECHO)

    def _req_led(self):
        from .regs_pb2 import Request
        return self._req_init(action = Request.LED)

    def _req_get_state(self, start, count):
        from .regs_pb2 import Request
        return self._req_init(action = Request.GET_STATE, start = start, count = count)

    def _req_set_state(self, start, payload):
        from .regs_pb2 import Request
        return self._req_init(action = Request.SET_STATE, start = start, payload = payload)

    def _req_get_samples(self, count, stream = False):
        from .regs_pb2 import Request
        return self._req_init(action = Request.SAMPLES, count = count, stream = stream )

    def _read(self):
        from time import sleep
        from Queue import Full
        from .regs_pb2 import Response

        buff = ''

        logger.debug('Starting mesage receiver thread.')
        print 'start'

        while self._t.is_alive():

            if not self._stream.isOpen():
                sleep(0.1)
                continue

            buff += self._stream.readall()
            if buff:
                msg, buff = self._deserialize_delimited(buff, Response)
                if msg: print 'response:\n%s'% msg
                while msg:
                    try:
                        self._queue.put(msg,timeout=0.1)
                        msg = None
                    except Full:
                        pass

            sleep(0.1)

        print 'the end'
        logger.warn('Terminating mesage receiver thread.')

    def _write_request(self, msg):
        from time import sleep
        while not self._stream.isOpen():
            sleep(0.1)
        buff = self._serialize_delimited(msg)
        self._stream.write(buff)


    def _read_response(self):
        from time import sleep
        from .regs_pb2 import Response
        while not self._stream.isOpen():
            sleep(0.1)
        msg = None
        while msg is None:
            msg, self._readbuffer = self._deserialize_delimited(self._readbuffer + self._stream.read(self._stream.inWaiting()), Response)
            sleep(0.1)
        return msg

    def handle(self, req, timeout= 1.0 ):
        from Queue import Empty
        if req: print 'request:\n%s'% req
        reqid = req.reqid
        self._write_request(req)
        return self._read_response()

    def echo(self, timeout=1.0 ):
        return self.handle(self._req_echo(), timeout=timeout )

    def get_state(self, start, count, timeout=1.0 ):
        return self.handle(self._req_get_state(start=start, count=count), timeout=timeout )

    def set_state(self, start, payload, timeout=1.0 ):
        return self.handle(self._req_set_state(start=start, payload=payload), timeout=timeout )

    def get_samples(self, count, stream = False, timeout=1.0 ):
        return self.handle(self._req_get_samples(count=count, stream = stream), timeout=timeout )

    def get_stream(self, count, timeout=1.0 ):
        pass # not implemented
