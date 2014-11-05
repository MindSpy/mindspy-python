#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [ 'MatchingStream' ]

from threading import RLock
from Queue import Empty, Full
import logging

from mindspy import CodedStream

logger = logging.getLogger(__name__)

def synchronized(obj):
    """Create synchronized container based on RLock.

    Usage:
        * as decorator
            @synchronized
            def fnc(): pass

            whith fnc as sfnc:
                sfnc()

            # or (automatic unwrapping)

            fnc()
        * as function
            data = synchronized(dict())
            with data as d:
                d[key] = value
    """

    class SynchronizedContainer:
        def __init__(self, obj):
            self._o = obj
            self._l = RLock()
        def __enter__(self):
            if self._l.__enter__():
                return self._o
        def __exit__(self, t, v, tb):
            self._l.__exit__(t, v, tb)
        def __call__(self, *a, **kw):
            with self as sfnc:
                return sfnc(*a, **kw)

    return SynchronizedContainer(obj)

class MatchingStream:
    """Stream that matches requests with requests.
    """
    def __init__(self, codedstream):
        if not isinstance(codedstream, CodedStream):
            raise TypeError("Expecting CodedStream instance.")
        self._stream = codedstream
        self._sdict = synchronized(dict())

    def put(self, req, block=True, timeout=None):
        """Put request to stream queue.
        """
        return self._stream.put(req, block=block, timeout=timeout)

    def get(self, reqid, block=True, timeout=None):
        """Get responses from stream queue to given request object.
        """
        yielded = False
        while True:
            try:
                # try to yield at least one response
                with self._sdict as d:
                    if reqid in d and d[reqid]:
                        yield d[reqid].pop()
                        yielded = True
                        #if not req.stream:
                        #    break

                # get one response and store it
                res = self._stream.get(block=block, timeout=timeout)
                with self._sdict as d:
                    if res.reqid not in d:
                        d[res.reqid] = []
                    d[res.reqid].insert(0, res)

                # prune the storage
                with self._sdict as d:
                    for k,v in d.items():
                        if not v:
                            del d[k]
            except Empty as e:
                if not yielded:
                    raise e
                else:
                    break