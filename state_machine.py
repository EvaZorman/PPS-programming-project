"""
State machine functionality.

This part will handle the states a router needs to keep track of. Each
router needs to track their own state with a state machine and act
according to the BGP protocol.
"""
import asyncio
import loguru

"""
These states functions need to implement
"""
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
#     close_connection,
#     send_keepalive_message,
#     send_notification_message,
#     send_open_message,
#     send_update_message,
# )


class BGPStateMachine:
    # I'd suggest to use the python-statemachine lib, but do whatever
    # feels best for you :)
    def __init__(self, local_id, local_hold_time, peer_ip):
        """ Class constructor """

        self.local_id = local_id
        self.local_hold_time = local_hold_time
        self.peer_ip = peer_ip

        self.peer_port = 0

        self.peer_id = None

        self.event_queue = []
        self.event_serial_number = 0

        # self.reader = None
        # self.writer = None
        # self.tcp_connection_established = False

        self.state = "Idle"
        self.connect_retry_counter = 0
        self.connect_retry_timer = 0
        self.connect_retry_time = 5
        self.hold_timer = 0
        self.hold_time = 0
        self.keepalive_timer = 0
        self.keepalive_time = 0

        self.logger = loguru.logger.bind(peer=f"{self.peer_ip}:{self.peer_port}", state=self.state)

        self.connect_retry_time = 5

        self.task_fsm = asyncio.create_task(self.fsm())
        self.task_decrease_hold_timer = asyncio.create_task(self.decrease_hold_timer())
        self.task_decrease_connect_retry_timer = asyncio.create_task(self.decrease_connect_retry_timer())
        self.task_decrease_keepalive_timer = asyncio.create_task(self.decrease_keepalive_timer())

    def __del__(self):
        """ Class destructor """

        self.close_connection()
        self.task_fsm.cancel()
        self.task_decrease_hold_timer.cancel()
        self.task_decrease_connect_retry_timer.cancel()
        self.task_decrease_keepalive_timer.cancel()

    def enqueue_event(self, event):
        """ Add new event to the event queue """

        # Add serial number to event for ease of debugging
        self.event_serial_number += 1

        event.serial_number = self.event_serial_number

        # In case Stop event is being enqueued flush the queue to expedite it

        """
        Event 2: ManualStop
        Definition: Should be called when a BGP ManualStop event is requested.
        Status: Mandatory
        """

        """ If we implement couple of Mandatory Events then we need it"""

        # if event.name in {"Event 2: ManualStop", "Event 8: AutomaticStop"}:
        #     self.event_queue.clear()

        self.event_queue.append(event)

        self.logger.opt(ansi=True, depth=1).debug(f"<cyan>[ENQ]</cyan> {event.name} [#{event.serial_number}]")

    def dequeue_event(self):
        """ Pick an event from the event queue """

        event = self.event_queue.pop(0)
        self.logger.opt(ansi=True, depth=1).debug(f"<cyan>[DEQ]</cyan> {event.name} [#{event.serial_number}]")
        return event

    def change_state(self, state):
        """ Change FSM state """

        assert state in {"Idle", "Connect", "Active", "OpenSent", "OpenConfirm", "Established"}

        self.logger.opt(depth=1).info(f"State: {self.state} -> {state}")
        self.state = state

        self.logger = loguru.logger.bind(peer=f"{self.peer_ip}:{self.peer_port}", state=self.state)

        if self.state == "Idle":
            self.connect_retry_timer = 0
            self.keepalive_timer = 0
            self.hold_timer = 0
            self.peer_port = 0
            self.close_connection()

    async def fsm(self):
        """ Finite State Machine loop """

        while True:
            if self.event_queue:
                event = self.dequeue_event()

                if self.state == "Idle":
                    await self.fsm_idle(event)

                if self.state == "Connect":
                    await self.fsm_connect(event)

                if self.state == "Active":
                    await self.fsm_active(event)

                if self.state == "OpenSent":
                    await self.fsm_opensent(event)

                if self.state == "OpenConfirm":
                    await self.fsm_openconfirm(event)

                if self.state == "Established":
                    await self.fsm_established(event)

            await asyncio.sleep(0.1)
