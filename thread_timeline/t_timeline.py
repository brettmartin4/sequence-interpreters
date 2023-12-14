from time import time
import os, pickle

from .timeline import Timeline
from .event import Event
#from sequence.kernel.quantum_manager import KET_STATE_FORMALISM
#from .quantum_manager_client import QuantumManagerClient

from test.support import interpreters


class ThreadedTimeline(Timeline):
    """
    Class for a simulation timeline with python subinterpreter support
    
    The Threaded Timeline class acts and behaves almost identically to the
    Parallel Timeline class except that it uses the developmental Interpreters
    module from version 3.12 of the Python/C API. There is one Threaded
    Timeline per thread (2 max per process). For events executed on nodes
    belonging to other timelines, an event buffer is maintained. These buffers
    are exchanged between timelines at regular synchronization intervals. All
    Threaded Timelines in a simulation communicate with a Quantum Manager
    Server for shared quantum states (not yet supported with Interpreters).

    Attributes:
        id (int): ID for the interpreter running the Threaded Timeline
            instance.
        foreign_entities (Dict[str, int]): mapping of object names on other
            threads to interpreter id.
        event_buffer(List[List[Event]]): stores events for execution on
            foreign entities; swapped during synchronization.
        lookahead (int): defines width of time window for execution
            (simulation time between synchronization).
        recv_channel (RecvChannel): Interpreter Receiver Channel in which data
            is received from another interpreter.
        send_channel (SendChannel): Interpreter Send Channel through which
            data is sent to another interpreter.
    """

    def __init__(self, recv_channel, send_channel, lookahead: int,
                 stop_time=float('inf')):
        """
        Constructor for ThreadedTimeline class.
        
        Also creates a quantum manager client, unless `qm_ip` and `qm_port`
        are both set to None. Removed for the purpose of the standalone
        timeline class.
        
        Args:
            recv_channel (RecvChannel): Cross-interpreter receiver channel.
            send_channel (SendChannel): Cross-interpreter sender channel.
            lookahead (int): sets the timeline lookahead time.
            stop_time (int): stop (simulation) time of simulation
                (default inf).
        """

        super(ThreadedTimeline, self).__init__(stop_time)

        # Threaded timeline class constructor vars:
        self.id = interpreters.get_current().id
        self.foreign_entities = {}
        self.event_buffer = [[] for _ in range(len(interpreters.list_all()))]
        self.lookahead = lookahead
        #if qm_ip is not None and qm_port is not None:
        #    self.quantum_manager = QuantumManagerClient(formalism, qm_ip, qm_port)

        self.recv_channel = recv_channel
        self.send_channel = send_channel

        #self.show_progress = False

        self.buffer_min_ts = float('inf')

        self.sync_counter = 0
        self.exchange_counter = 0
        self.computing_time = 0
        self.communication_time = 0


    def schedule(self, event: 'Event'):
        """
        Method to schedule an event.
        
        Args:
            event (Event): Event to be scheduled on current timeline.
        """

        # Check if event is on another thread. If so, add it to the
        # appropriate event buffer
        if type(event.process.owner) is str \
                and event.process.owner in self.foreign_entities:
            # Get the timestamp of the event to be scheduled
            self.buffer_min_ts = min(self.buffer_min_ts, event.time)
            # Get the interpreter ID for the event
            tl_id = self.foreign_entities[event.process.owner]
            # Add event to the event buffer under the respective process ID
            self.event_buffer[tl_id].append(event)
            self.schedule_counter += 1
        else:
            # Otherwise, schedule on current timeline
            super(ThreadedTimeline, self).schedule(event)


    def top_time(self) -> float:
        """
        Method to get the timestamp of the event in the local queue with the
        lowest time and priority.

        Used for the conservative synchronization algorithm.
        If the event queue is empty, returns infinity.

        Returns:
            float: Time of the event with lowest time and priority.
        """

        if len(self.events) > 0:
            return self.events.top().time
        else:
            return float('inf')
        

    def run(self):
        """Runs the simulation until stop time is reached."""
        
        while self.time < self.stop_time:
            # Get current time
            tick = time()
            # Get timestamp of the soonest event in the LOCAL queue
            min_time = min(self.buffer_min_ts, self.top_time())

            for buf in self.event_buffer:
                buf.append(min_time)

            # Get index of event buffer that contains all other foreign events
            # and send over interpreter channel.
            buf_index = 1 - int(self.id)
            self.send_channel.send_nowait(pickle.dumps((self.event_buffer[buf_index],)))

            # Receive event buffer from other timeline
            recv_buf = pickle.loads(self.recv_channel.recv(_delay=0))[0]
            inbox = []
            inbox.append(recv_buf)

            # Record time taken to communicate data between interpreters
            self.communication_time += time() - tick

            # Reset event buffer (result of communication stored in "inbox")
            for buff in self.event_buffer:
                buff.clear()
            self.buffer_min_ts = float('inf')

            # Go through all events that were gathered from other timelines
            for events in inbox:
                min_time = min(min_time, events.pop())
                # Iterate over all events in the events list, incrememnting
                # the exchange counter and scheduling the event
                for event in events:
                    # TODO: Included this check because an earlier version of
                    # this file was loading the min times as events, causing
                    # an error. Check if can remove later.
                    if not isinstance(event, Event):
                        continue
                    self.exchange_counter += 1
                    self.schedule(event)

            # Throw AssertionError if min_time is less than the timeline's
            # current time
            assert min_time >= self.time

            # Exit current simulation loop if the sim stop time is reached
            if min_time >= self.stop_time:
                break

            # Increment synchronization window counter
            self.sync_counter += 1

            # Time up until next synchronization window
            sync_time = min(min_time + self.lookahead, self.stop_time)
            self.time = min_time

            tick = time()
            # Iterate over all events as long as the event with the lowest
            # time is scheduled to occur before the end of the synch window
            while len(self.events) > 0 and self.events.top().time < sync_time:
                # Retrieve event with lowest time & priority, verify validity
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                    event.process.owner)
                # Set timeline's time to time of current event and run the
                # process associated with the event
                self.time = event.time
                event.process.run()
                self.run_counter += 1
            # EDIT: Removed quantum manager reference for interpreters demo
            #if isinstance(self.quantum_manager, QuantumManagerClient):
            #    self.quantum_manager.flush_before_sync()
            self.computing_time += time() - tick


    def add_foreign_entity(self, entity_name: str, foreign_id: int):
        """
        Adds the name of an entity on another threaded timeline.

        Args:
            entity_name (str): name of the entity on another threaded
                timeline.
            foreign_id (int): id of the interpreter containing the entity.
        """

        self.foreign_entities[entity_name] = foreign_id
