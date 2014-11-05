
"""
ldr.py

Display analog data from Arduino using Python (matplotlib)

Author: Mahesh Venkitachalam
Website: electronut.in
"""
from Queue import Empty

from collections import deque
from numpy import linspace
from threading import Thread, Event
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mindspy import Request, Response, CodedSubprocessStream, MatchingStream, MindSpy, State
from mindspy.matchingstream import synchronized

class StoppableLoopDaemonThread(Thread):
    def __init__(self):
        super(StoppableLoopDaemonThread, self).__init__()
        self.daemon = True
        self._stop = Event()
    def stop(self):
        self._stop.set()
    def run(self):
        while not self._stop.is_set():
            self.loop()
    def loop(self):
        raise Exception("Not implemented.")

class MessageConsumer(StoppableLoopDaemonThread):
    def __init__(self, gen, buff):
        super(MessageConsumer, self).__init__()
        self._buffer = buff
        self._generator = gen
    def loop(self):
        try:
            samples = self._generator.next()
            with self._buffer as buff:
                for s in samples:
                    for buf,val in zip(buff,s.payload):
                        buf.pop()
                        buf.appendleft(val)
        except Empty:
            pass

class Animation(animation.FuncAnimation):
    def __init__(self, fig, buffer, axes, plotlen, fsamp, **kwargs):
        self._buffer = buffer
        self._axes = axes
        self._plotlen = plotlen
        self._fsamp = fsamp
        super(Animation, self).__init__(fig, self.update, **kwargs)
    def update(self, *a, **kw):
        with self._buffer as buff:
            for a,x in zip(self._axes,buff):
                a.set_data(linspace(0, 1.*self._plotlen/self._fsamp, self._plotlen, endpoint=False), x)

if __name__ == '__main__':

    cs = CodedSubprocessStream('../firmware/test/server', Request, Response)
    #cs = CodedSerialStream('/dev/ttyACM0', 115200, 1.0, Request, Response)

    dev = MindSpy(MatchingStream(cs))
    sensors = list(dev.sensors())

    fsamp = 200 # sample rate 200Hz
    nchan = 4 # 4 channels
    fsig = 10  # signal frequency 10Hz

    plotlen = 400 # graph width 400px
    amp = 255 # amplitude 255

    print sensors[0].getModelName().next()
    states = [
        State(payload=fsamp, address=0),
        State(payload=nchan, address=1),
        State(payload=fsig, address=2),
        State(payload=amp, address=3)
    ]
    # set sensor state
    sensors[0].setState(states)
    # sample generator
    data = sensors[0].getSamples(3, stream=True, timeout=1.0)
    # buffer for plots
    buffer = synchronized([ deque([0.0]*plotlen) for i in range(nchan) ])

    # set up axes
    f, axarr = plt.subplots(nchan, sharex=True)
    for ax in axarr:
        ax.set_xlim(0, 1.*plotlen/fsamp)
        ax.set_ylim(-150, 150)
    axes = [ ax.plot([], [])[0] for ax in axarr ]

    # set up animation
    anim = Animation(f, buffer, axes, plotlen, fsamp)

    # start message consumer
    t = MessageConsumer(data, buffer)
    t.start()

    # show plot
    print('plotting data...')
    try:
        plt.show()
    except KeyboardInterrupt:
        print('exiting')

    # terminate


