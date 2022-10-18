"""
State machine functionality.

This part will handle the states a router needs to keep track of. Each
router needs to track their own state with a state machine and act
according to the BGP protocol.
"""
import asyncio
import loguru
from enum import Enum

from fsm_active import fsm_active
from fsm_connect import fsm_connect
from fsm_established import fsm_established
from fsm_idle import fsm_idle
from fsm_openconfirm import fsm_openconfirm
from fsm_opensent import fsm_opensent

from timers import (
    decrease_connect_retry_timer,
    decrease_hold_timer,
    decrease_keepalive_timer,
)

# from Sams Work import (
#     send_keepalive_message,
#     send_open_message,
#     send_update_message,
# )

# from errors import (
# notification_message,
# )


class State(Enum):
    IDLE = 1
    CONNECT = 2
    ACTIVE = 3
    OPEN_SENT = 4
    OPEN_CONFIRM = 5
    ESTABLISHED = 6


class BGPStateMachine:
    """
    TODO Q: this is constructed in a way that we should only create a SM once we have a connection to another peer

    I was under the impression each router would need its own state machine that isn't necessarily connected to
    a peer. With this, we can't just create a router and assign a SM to it.
    """
    def __init__(self, local_id, local_hold_time, peer_ip):
        """Class constructor"""

        self.local_id = local_id
        self.local_hold_time = local_hold_time
        self.peer_ip = peer_ip

        self.peer_port = 0

        self.peer_id = None

        self.event_queue = []
        self.event_serial_number = 0

        self.reader = None
        self.writer = None
        self.tcp_connection_established = False

        self.state = State.IDLE
        self.connect_retry_counter = 0
        self.connect_retry_timer = 0
        self.connect_retry_time = 5
        self.hold_timer = 0
        self.hold_time = 0
        self.keepalive_timer = 0
        self.keepalive_time = 0

        self.logger = loguru.logger.bind(
            peer=f"{self.peer_ip}:{self.peer_port}", state=self.state
        )

        self.connect_retry_time = 5

        self.task_fsm = asyncio.create_task(self.fsm())
        self.task_decrease_hold_timer = asyncio.create_task(decrease_hold_timer(self))
        self.task_decrease_connect_retry_timer = asyncio.create_task(
            decrease_connect_retry_timer(self)
        )
        self.task_decrease_keepalive_timer = asyncio.create_task(
            decrease_keepalive_timer(self)
        )

    def __del__(self):
        """Class destructor"""

        # self.close_connection() should be done by the router
        self.task_fsm.cancel()
        self.task_decrease_hold_timer.cancel()
        self.task_decrease_connect_retry_timer.cancel()
        self.task_decrease_keepalive_timer.cancel()

    # TODO who creates events? we're just passing strings to this method
    def enqueue_event(self, event):
        """Add new event to the event queue"""

        # Add serial number to event for ease of debugging
        self.event_serial_number += 1
        event.set_event_serial_num(self.event_serial_number)

        # In case Stop event is being enqueued flush the queue to expedite it

        """ If we implement Manual Stop and Automatic Stop couple of Mandatory Events then we need it"""

        # if event.name in {"Event 2: ManualStop", "Event 8: AutomaticStop"}:
        #     self.event_queue.clear()

        self.event_queue.append(event)
        self.logger.opt(ansi=True, depth=1).debug(
            f"<cyan>[ENQ]</cyan> {event.get_name()} [#{event.get_serial_num()}]"
        )

    def dequeue_event(self):
        """Pick an event from the event queue"""

        event = self.event_queue.pop(0)
        self.logger.opt(ansi=True, depth=1).debug(
            f"<cyan>[DEQ]</cyan> {event.get_name()} [#{event.get_serial_num()}]"
        )
        return event

    def change_state(self, state):
        """Change FSM state"""

        assert state in State

        self.logger.opt(depth=1).info(f"State: {self.state} -> {state}")
        self.state = state

        self.logger = loguru.logger.bind(
            peer=f"{self.peer_ip}:{self.peer_port}", state=self.state
        )

        if self.state == State.IDLE:
            self.connect_retry_timer = 0
            self.keepalive_timer = 0
            self.hold_timer = 0
            self.peer_port = 0
            # self.close_connection() this should probably be done by the router and not by the fsm

    async def fsm(self):
        """Finite State Machine loop"""

        while True:
            if self.event_queue:
                event = self.dequeue_event()

                if self.state == State.IDLE:
                    await fsm_idle(self, event)

                if self.state == State.CONNECT:
                    await fsm_connect(self, event)

                if self.state == State.ACTIVE:
                    await fsm_active(self, event)

                if self.state == State.OPEN_SENT:
                    await fsm_opensent(self, event)

                if self.state == State.OPEN_CONFIRM:
                    await fsm_openconfirm(self, event)

                if self.state == State.ESTABLISHED:
                    await fsm_established(self, event)

            await asyncio.sleep(0.1)
