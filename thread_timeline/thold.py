#from numpy.random import choice, exponential
from typing import List, TYPE_CHECKING
# EDIT: Added for interpreters demo (replaced numpy choice and exponential imports):
from random import choice, expovariate

from .process import Process
from .event import Event

if TYPE_CHECKING:
    from .t_timeline import ThreadedTimeline


class TholdNode:
    """
    Class for a THOLD Node for use in a Threaded hold simulation model.

    Based on the "Parallel hold (PHOLD) model, "commonly used to benchmark
    parallel and distributed discrete-event simulators."
    Threaded hold (THOLD) takes PSeQUeNCe's MPI-driven PHOLD node and modifies
    it to support sub-interpreters from Python/C API's developmental
    Interpreter's module (Python 3.12.0+).

    According to the docs for another, unrelated DES package, SIMULUS, the
    PHOLD model consists of a number of nodes that are passing messages to one
    another (https://simulus.readthedocs.io/en/latest/parsim-sync.html). In
    this context, THOLD Nodes in a Threaded Timeline generate a prescribed
    number of events and communicate them between interpreters, executing them
    between synchronization windows.

    Attributes:
        name (int): ID for the current TholdNode running the Threaded Timeline
            instance.
        timeline (ThreadedTimeline): Threaded Timeline current node is
            associated with.
        init_work (int): Overall number of events to be generated.
        lookahead (int): Timeline lookahead time.
        neighbors (List[str]): List of other Nodes on current Threaded
            Timeline.
    """

    def __init__(self, name: 'str', timeline: 'ThreadedTimeline',
                 init_work: int, lookahead: int, neighbors: List[str]):
        """
        Constructor for TholdNode class.
        
        Args:
            name (str): Name of the node.
            timeline (ThreadedTimeline): Threaded Timeline current node is
                associated with.
            init_work (int): Overall number of events to be generated.
            lookahead (int): Timeline lookahead time.
            neighbors (List[str]): List of other Nodes on current Threaded
                Timeline.
        """

        self.name = name
        self.timeline = timeline
        timeline.entities[name] = self
        self.init_work = init_work
        self.lookahead = lookahead
        self.neightbors = neighbors

    def generate_event(self) -> Event:
        """
        Method for generating and returning an Event with an empty Process.

        PSeQUeNCe's PholdNode used the numpy.random.exponential() method to
        generate random numbers based on the lookahead time, but since
        Interpreters does not yet support numpy, the random.expovariate()
        method is used, which takes as an argument the inverse of whatever
        value is passed to numpy.random.exponential() to achieve similar
        results.

        Returns:
            Event: Generated Event
        """
        next_str = str(choice(self.neightbors))
        entity = self.timeline.get_entity_by_name(next_str)
        if entity is None:
            process = Process(next_str, 'get', [])
        else:
            process = Process(entity, 'get', [])
        #event = Event(self.timeline.now() + self.lookahead + int(
        #    exponential(self.lookahead)), process)
        event = Event(self.timeline.now() + self.lookahead + 
                      int(expovariate(1/self.lookahead)), process)
        return event

    def init(self):
        """
        Initialization function for the TholdNode.

        For the prescribed amount of work, node will generate events and
        schedule them on the associated ThreadedTimeline.
        """
        for _ in range(self.init_work):
            event = self.generate_event()
            self.timeline.schedule(event)

    def get(self):
        """Method to produceand schedule a single Event."""
        event = self.generate_event()
        self.timeline.schedule(event)
