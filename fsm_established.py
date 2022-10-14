from errors import FiniteStateMachineError
from state_machine import State

"""
For this part I need to see Bgp message and error clas coding
In the skeleton made by EVA, I saw she created class for
CeaseError, HoldTimeExpiredError so on.

Here I only implemented mandatory ones (not all events)
"""


async def fsm_established(cls, event):
    """State Machine - Established state"""

    """
    Event 11:   KeepaliveTimer_Expires
    Definition: Called when the KeepAliveTimer expires.
    Action:     Send Keepalive message if the state of FSM is ST_OPENCONFIRM
                or ST_ESTABLISHED, close BGP connection if state is others
    Status: Mandatory
    """
    if event.get_name() == "Event 11: KeepaliveTimer_Expires":
        cls.logger.info(event.get_name())

        # Send KEEPALIVE message
        await cls.send_keepalive_message()

        # Restart KeepaliveTimer
        cls.keepalive_timer = cls.keepalive_time

    else:
        # Send a NOTIFICATION message with the Error Code Finite State Machine Error
        cls.notificaion_message(FiniteStateMachineError)

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1

        cls.change_state(State.IDLE)
