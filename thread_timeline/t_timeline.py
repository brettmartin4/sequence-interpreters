from time import time
import pickle

# SeQUeNCe imports
from .timeline import Timeline
from .event import Event
#from sequence.kernel.quantum_manager import KET_STATE_FORMALISM
#from .quantum_manager_client import QuantumManagerClient

# Interpreter imports
from test.support import interpreters
import os


class ThreadedTimeline(Timeline):
    """Class for a simulation timeline with python subinterpreter support
    
    The Threaded Timeline class acts and behaves almost identically to the
    Parallel Timeline class except that it uses the developmental Interpreters
    module from version 3.12 of the Python/C API.
    There is one Threaded Timeline per thread (2 max per process).
    For events executed on nodes belonging to other timelines, an event buffer is maintained.
    These buffers are exchanged between timelines at regular synchronization intervals.
    All Threaded Timelines in a simulation communicate with a Quantum Manager Server for shared quantum states.

    Attributes:
        id (int): ID for the interpreter running the Threaded Timeline instance.
        foreign_entities (Dict[str, int]): mapping of object names on other threads to interpreter id.
        event_buffer(List[List[Event]]): stores events for execution on foreign entities;
            swapped during synchronization.
        lookahead (int): defines width of time window for execution (simulation time between synchronization).
        recv_fifo (str): Name of the FIFO in which data is received from another interpreter.
        send_fifo (str): Name of the FIFO through which data is sent to another interpreter.
    """

    def __init__(self, recv_file, send_file, mutex, lookahead: int, stop_time=float('inf')):
        """Constructor for ThreadedTimeline class.
        
        Also creates a quantum manager client, unless `qm_ip` and `qm_port` are both set to None. Removed
        for the purpose of the standalone timeline class.
        
        Args:
            recv_fifo (str): name of receiver FIFO in memory.
            send_fifo (str): name of sender FIFO in memory.
            lookahead (int): sets the timeline lookahead time.
            stop_time (int): stop (simulation) time of simulation (default inf).
        """

        super(ThreadedTimeline, self).__init__(stop_time)

        # Threaded timeline class constructor vars:
        self.id = interpreters.get_current().id
        self.foreign_entities = {}
        self.event_buffer = [[] for _ in range(len(interpreters.list_all()))]
        self.lookahead = lookahead
        #if qm_ip is not None and qm_port is not None:
        #    self.quantum_manager = QuantumManagerClient(formalism, qm_ip, qm_port)

        self.recv_file = recv_file
        self.send_file = send_file
        self.mutex = mutex

        #self.show_progress = False

        self.buffer_min_ts = float('inf')

        self.sync_counter = 0
        self.exchange_counter = 0
        self.computing_time = 0
        self.communication_time = 0

        self.read_ops = 0
        self.write_ops = 0


    def schedule(self, event: 'Event'):
        """Method to schedule an event."""

        # Check if event is on another thread. If so, add it to the appropriate event buffer
        if type(event.process.owner) is str \
                and event.process.owner in self.foreign_entities:
            # Get the timestamp of the event to be scheduled
            self.buffer_min_ts = min(self.buffer_min_ts, event.time)
            # Get the interpreter ID for the event
            tl_id = self.foreign_entities[event.process.owner]
            # Add the event to the event buffer under the respective process ID
            self.event_buffer[tl_id].append(event)
            self.schedule_counter += 1
        else:
            # Otherwise, schedule on current timeline
            super(ThreadedTimeline, self).schedule(event)


    def top_time(self) -> float:
        """Method to get the timestamp of the soonest event in the local queue.

        Used for the conservative synchronization algorithm.
        If the event queue is empty, returns infinity.
        """

        if len(self.events) > 0:
            return self.events.top().time
        else:
            return float('inf')
        

    def send_event_buffer_to_file(self, index):

        with self.mutex:   # Acquire mutex lock
            #print(f"{self.id} Writing event buffer of size {len(self.event_buffer[0])} or {len(self.event_buffer[1])}\n")
            with open(self.send_file, 'wb') as file:
                # Write data as tuple to entire event buffer can be written at once
                pickle.dump((self.event_buffer[index],), file)
                self.write_ops += 1


    def receive_event_buffer_from_file(self):

        # Repeat until the read file populates.
        # Depending on how SeQUeNCe timelines handle read/write ops between
        # synchronization windows, I may be able to remove the while loop.
        # TODO: Verify this later...
        while True:
            # Added this because the subinterpreter kept getting hung up on the last
            # read operation and I have zero clue why.
            if os.path.exists("signal.txt"):
                return [float('inf')]
            try:
                with self.mutex:   # Acquire mutex lock
                    with open(self.recv_file, 'rb') as file:
                        #file_size = os.path.getsize(file)
                        file_size = os.fstat(file.fileno()).st_size

                        if file_size == 0:
                            continue

                        # Load data as tuple, take event buffer list from start index
                        data = pickle.load(file)[0]
                    # Clear file when done reading
                    with open(self.recv_file, 'wb') as file:
                        pass
                    self.read_ops += 1
                    return data
            except IOError as e:
                if e.errno != 11:  # Ignore "Resource temporarily unavailable" error
                    raise
                pass
        

    def run(self):
        """Runs the simulation until stop time is reached."""
        
        while self.time < self.stop_time:
            # Get current time
            tick = time()
            # Get timestamp of the soonest event in the LOCAL queue
            min_time = min(self.buffer_min_ts, self.top_time())

            for buf in self.event_buffer:
                buf.append(min_time)

            # UPDATE #

            # Use FIFO for comms instead of MPI (Remove once cpython fixes inter-interpreter channel support)
            # The following lines until "END UPDATE" are all meant to replace the following line from the parallel timeline:
            #inbox = MPI.COMM_WORLD.alltoall(self.event_buffer)

            # Get index of event buffer that contains all other foreign events
            buf_index = 1 - int(self.id)

            #if self.write_ops >= 998:
                #print(f"Interp {self.id} sending buffer of size {len(self.event_buffer[0])} or {len(self.event_buffer[1])}")
            # Send data from current timeline to queue file
            self.send_event_buffer_to_file(buf_index)

            # Load data from other timelines from other queue file
            recv_buf = self.receive_event_buffer_from_file()
            #inbox = [a + b for a, b in zip(self.event_buffer, recv_buf, strict=False)]
            inbox = []
            inbox.append(recv_buf)

            # END UPDATE #

            self.communication_time += time() - tick

            for buff in self.event_buffer:
                buff.clear()
            self.buffer_min_ts = float('inf')

            # Go through all events that were gathered using MPI from other timelines
            for events in inbox:
                # Find the current event time (of soonest event)
                min_time = min(min_time, events.pop())
                # Iterate over all events in the events list, incrememnting the exchange counter and scheduling the event
                for event in events:
                    if not isinstance(event, Event):
                        continue
                    self.exchange_counter += 1
                    self.schedule(event)

            # Throw AssertionError if min_time is less than the timeline's current time
            assert min_time >= self.time

            # Exit current simulation loop if the sim stop time is reached
            if min_time >= self.stop_time:
                break

            # Increment synchronization window counter
            self.sync_counter += 1

            sync_time = min(min_time + self.lookahead, self.stop_time)
            self.time = min_time

            tick = time()
            while len(self.events) > 0 and self.events.top().time < sync_time:
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                    event.process.owner)
                self.time = event.time
                event.process.run()
                self.run_counter += 1
            # EDIT: Removed quantum manager reference for interpreters demo
            #if isinstance(self.quantum_manager, QuantumManagerClient):
            #    self.quantum_manager.flush_before_sync()
            self.computing_time += time() - tick


    def add_foreign_entity(self, entity_name: str, foreign_id: int):
        """Adds the name of an entity on another parallel timeline.

        Args:
            entity_name (str): name of the entity on another parallel timeline.
            foreign_id (int): id of the process containing the entity.
        """

        self.foreign_entities[entity_name] = foreign_id
