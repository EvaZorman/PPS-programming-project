"""
State machine functionality.

This part will handle the states a router needs to keep track of. Each
router needs to track their own state with a state machine and act
according to the BGP protocol.
"""
import logging

from states import IdleState, EstablishedState

from timers import (
    decrease_connect_retry_timer,
    decrease_hold_timer,
    decrease_keepalive_timer,
)

logger = logging.getLogger("BGP")


class BGPStateMachine:
    """
    I was under the impression each router would need its own state machine
    that isn't necessarily connected to a peer. With this, we can't just
    create a router and assign an SM to it.
    """

    def __init__(self, local_id, local_hold_time, peer_ip):
        """Class constructor"""

        self.states = {}
        self.peer_ip = peer_ip

        for i in self.peer_ip:
            self.states[i] = IdleState()

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

        self.local_id = local_id
        self.local_hold_time = local_hold_time

        self.peer_port = 0
        self.peer_id = None

    def switch_state(self, peer, event):
        self.states[peer] = self.states[peer].on_event(self, event)

    def get_state(self, peer):
        try:
            return self.states[peer]
        except KeyError:
            return

    def all_setup(self):
        for i in self.peer_ip:
            if not isinstance(self.states[i], EstablishedState):
                return False
        return True
