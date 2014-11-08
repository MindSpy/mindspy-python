
__all__ = [ 'MindSpy', 'Sensor' ]

from itertools import count, imap
from time import time
from random import randint
import logging

from .matchingstream import MatchingStream
from .proto import Request

logger = logging.getLogger(__name__)

class Sensor(object):
    def __init__(self, device, module, name):
        if not isinstance(device, MindSpy):
            raise TypeError("Expecting MindSpy instance.")
        self._dev = device
        self._mod = module
        self._name = name

    def echo(self, timeout=1.0, **kw ):
        kw.update(module= self._mod)
        return self._dev.echo(timeout=timeout, **kw)

    def getModelName(self, timeout=1.0, **kw ):
        kw.update(module= self._mod)
        return self._dev.getModelName(timeout=timeout, **kw)

    def getState(self, addresses, timeout=1.0, **kw ):
        kw.update(module= self._mod)
        return self._dev.getState(addresses, timeout=timeout, **kw)

    def getSamples(self, count, timeout=1.0, **kw ):
        kw.update(module= self._mod)
        return self._dev.getSamples(count, timeout=timeout, **kw)

    def setState(self, states, timeout=1.0, **kw ):
        kw.update(module= self._mod)
        return self._dev.setState(states, timeout=timeout, **kw)

class MindSpy(object):

    @staticmethod
    def _timestamp():
        return int(time()*1e6)  #in micros

    @staticmethod
    def _id():
        return randint(0, 2**32-1)

    _seq_counter = count()

    @classmethod
    def _seq(cls):
        return cls._seq_counter.next()

    def __init__(self, stream):
        if not isinstance(stream, MatchingStream):
            raise TypeError("Expecting MatchingStream instance.")
        self._stream = stream

    def _handle(self, req, timeout=1.0, extract=None):
        if not extract:
            extract = lambda x:x
        # send request to stream queue
        self._stream.put(req, timeout=timeout)
        # receive responses from stream queue
        result = self._stream.get(req.reqid, timeout=timeout)
        # extract values from the reponses
        return imap(extract, result)

    def _req_init(self, **kw):
        req = Request()
        req.timestamp = self._timestamp()
        req.reqid = self._id()

        for k,v in kw.items():
            if hasattr(req, k):
                setattr(req, k, v)

        return req

    def _req_echo(self, **kw):
        req = self._req_init(**kw)
        return req

    def _req_get_model_name(self, **kw):
        req = self._req_init(**kw)
        req.getModelName.MergeFromString('')
        return req

    def _req_get_state(self, addresses, **kw):
        req = self._req_init(**kw)
        req.getState.addresses.extend(addresses)
        return req

    def _req_set_state(self, states, **kw):
        req = self._req_init(**kw)
        req.setState.states.extend(states)
        return req

    def _req_get_samples(self, count, **kw):
        req = self._req_init(**kw)
        req.getSamples.count = count
        return req

    def echo(self, timeout=1.0, **kw ):
        return self._handle(self._req_echo(**kw), timeout=timeout)

    def getModelName(self, timeout=1.0, **kw ):
        return self._handle(self._req_get_model_name(**kw), timeout=timeout, extract=lambda msg: msg.modelName)

    def getState(self, addresses, timeout=1.0, **kw ):
        return self._handle(self._req_get_state(addresses, **kw), timeout=timeout, extract=lambda msg: msg.states)

    def setState(self, states, timeout=1.0, **kw ):
        return self._handle(self._req_set_state(states, **kw), timeout=timeout, extract=lambda msg: None )

    def getSamples(self, count, timeout=1.0, **kw ):
        return self._handle(self._req_get_samples(count, **kw), timeout=timeout, extract=lambda msg: msg.samples )

    def sensors(self, timeout = 1.0):
        for res in self._handle(self._req_get_model_name(), timeout=timeout ):
            yield Sensor(self, res.module, res.modelName)