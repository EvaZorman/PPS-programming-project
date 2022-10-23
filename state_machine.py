"""
State machine functionality.

This part will handle the states a router needs to keep track of. Each
router needs to track their own state with a state machine and act
according to the BGP protocol.
"""
from states import IdleState

from timers import (
    decrease_connect_retry_timer,
    decrease_hold_timer,
    decrease_keepalive_timer,
)


class BGPStateMachine:
    """
    I was under the impression each router would need its own state machine
    that isn't necessarily connected to a peer. With this, we can't just
    create a router and assign an SM to it.
    """

    def __init__(self, local_id, local_hold_time, peer_ip):
        """Class constructor"""

        self.states = {}
        for i in peer_ip:
            print(f"peer id: {i}, type: {type(i)}")
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
        self.peer_ip = peer_ip

        self.peer_port = 0
        self.peer_id = None

    def switch_state(self, peer, event):
        self.states[peer] = self.states[peer].on_event(self, event)

    def get_state(self, peer):
        try:
            return self.states[peer]
        except KeyError:
            return
