from errors import FiniteStateMachineError

"""
For this part I need to see Bgp message and error clas coding
In the skeleton made by EVA, I saw she created class for
CeaseError, HoldTimeExpiredError so on.

Here I only implemented mandatory ones (not all events)

"""


async def fsm_established(self, event):
    """State Machine - Established state"""

    """
    Event 11:   KeepaliveTimer_Expires
    Definition: Called when the KeepAliveTimer expires.
    Action:     Send Keepalive message if the state of FSM is ST_OPENCONFIRM
                or ST_ESTABLISHED, close BGP connection if state is others
    Status: Mandatory
    """

    if event.name == "Event 11: KeepaliveTimer_Expires":
        self.logger.info(event.name)

        # Send KEEPALIVE message
        await self.send_keepalive_message()

        # Restart KeepaliveTimer
        self.keepalive_timer = self.keepalive_time

    else:
        # Send a NOTIFICATION message with the Error Code Finite State Machine Error
        self.notificaion_message(FiniteStateMachineError)

        # Increment the ConnectRetryCounter by 1
        self.connect_retry_counter += 1

        self.change_state("Idle")
