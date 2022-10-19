"""
State machine functionality.

This part will handle the states a router needs to keep track of. Each
router needs to track their own state with a state machine and act
according to the BGP protocol.
"""
import loguru

from states import IdleState

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


class BGPStateMachine:
    """
    I was under the impression each router would need its own state machine
    that isn't necessarily connected to a peer. With this, we can't just
    create a router and assign a SM to it.
    """

    def __init__(self, local_id, local_hold_time, peer_ip):
        """Class constructor"""

        self.state = IdleState()

        self.event_queue = []
        self.event_serial_number = 0

        self.connect_retry_counter = 0
        self.connect_retry_timer = 0
        self.connect_retry_time = 5

        self.hold_timer = 0
        self.hold_time = 0

        self.keepalive_timer = 0
        self.keepalive_time = 0

        self.connect_retry_time = 5

        self.logger = loguru.logger

        self.local_id = local_id
        self.local_hold_time = local_hold_time
        self.peer_ip = peer_ip

        self.peer_port = 0
        self.peer_id = None

    def switch_state(self, event):
        self.state = self.state.on_event(self, event)

    def get_state(self):
        return self.state

    # def enqueue_event(self, event):
    #     """Add new event to the event queue"""
    #
    #     # Add serial number to event for ease of debugging
    #     self.event_serial_number += 1
    #     event.set_event_serial_num(self.event_serial_number)
    #
    #     # In case Stop event is being enqueued flush the queue to expedite it
    #
    #     # If we implement Manual Stop and Automatic Stop couple of Mandatory
    #     # Events then we need it
    #
    #     # if event.name in {"Event 2: ManualStop", "Event 8: AutomaticStop"}:
    #     #     self.event_queue.clear()
    #
    #     self.event_queue.append(event)
    #     self.logger.opt(ansi=True, depth=1).debug(
    #         f"<cyan>[ENQ]</cyan> {event.get_name()} [#{event.get_serial_num()}]"
    #     )
    #
    # def dequeue_event(self):
    #     """Pick an event from the event queue"""
    #
    #     event = self.event_queue.pop(0)
    #     self.logger.opt(ansi=True, depth=1).debug(
    #         f"<cyan>[DEQ]</cyan> {event.get_name()} [#{event.get_serial_num()}]"
    #     )
    #     return event
