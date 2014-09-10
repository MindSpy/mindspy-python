import signal

from .regs_pb2 import Request, Response

class MindSpy(object):
  def __init__(self):
    self._req = Request()
    self._res = Response()

  @staticmethod
  def _timestamp():
    from time import time
    return int(time())

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
  def _deserialize_delimited(serialized, message):
    count, token = MindSpy._decode_varint(serialized)
    rest = serialized[token:token+count]
    message.MergeFromString(rest)
    return message, serialized[token+count:]

  def _req_init(self):
    self._req.Clear()
    self._req.timestamp = self._timestamp()
    return self._req

  def _req_echo(self):
    req = self._req_init()
    req.action = Request.ECHO
    return self._serialize_delimited(req)

  def _req_led(self):
    req = self._req_init()
    req.action = Request.LED
    return self._serialize_delimited(req)

  def _req_get_state(self, start, count):
    req = self._req_init()
    req.action = Request.GET_STATE
    req.start = start
    req.count = count
    return self._serialize_delimited(req)

  def _req_set_state(self, start, payload):
    req = self._req_init()
    req.action = Request.SET_STATE
    req.start = start
    req.payload = payload
    return self._serialize_delimited(req)

  def _req_get_samples(self, count, stream = False):
    req = self._req_init()
    req.action = Request.SAMPLES
    req.count = count
    req.stream = stream
    return self._serialize_delimited(req)

  def _res_all(self, serialized):
    msg, rest = self._deserialize_delimited(serialized, self._res)
    return msg, rest

  def handle(self, req, stream):
      stream.write(req)
      buff = stream.readall()
      while True:
          msg, buff = self._res_all(buff)
          yield msg
          buff += stream.readall()
          if not buff:
              break

  def handle_echo(self, stream, *args, **kwargs):
      return self.handle(self._req_echo(*args, **kwargs), stream)

  def handle_get_state(self, stream, *args, **kwargs):
      return self.handle(self._req_get_state(*args, **kwargs), stream)

  def handle_set_state(self, stream, *args, **kwargs):
      return self.handle(self._req_set_state(*args, **kwargs), stream)

  def handle_get_samples(self, stream, *args, **kwargs):
      return self.handle(self._req_get_samples(*args, **kwargs), stream)





