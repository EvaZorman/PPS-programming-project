import asyncio

# import messages
import errors
from errors import FiniteStateMachineError
# From Sam


async def fsm_opensent(self, event):
    """ Opensent state """

    if event.name == "Event 18: TcpConnectionFails":
        self.logger.info(event.name)

        # Close the TCP connection
        self.close_connection()

        # Restart the ConnectRetryTimer
        self.connect_retry_timer = self.connect_retry_time

        # Change state to Active
        self.change_state("Active")

    """
           Event 19: BGPOpen
           Definition: Should be called when a BGP Open message was
                       received from the peer.
           Status: Mandatory
    """

    if event.name == "Event 19: BGPOpen":

        self.logger.info(event.name)

        message = event.message

        # Set the BGP ConnectRetryTimer to zero
        self.connect_retry_timer = 0

        # Send a KeepAlive message
        await self.send_keepalive_message()

        # I selected a Random value
        self.hold_time = 60

        # Set a KeepAliveTimer
        self.keepalive_time = self.hold_time
        self.keepalive_timer = self.keepalive_time

        # Change state to OpenConfirm
        self.change_state("OpenConfirm")

    if event.name in {"Event 21: BGPHeaderErr", "Event 22: BGPOpenMsgErr"}:
        self.logger.info(event.name)

        message = event.message

        # Send a NOTIFICATION message with the appropriate error code
        await self.notification_message(message.message_error_code, message.message_error_subcode)

        # Increment ConnectRetryCounter
        self.connect_retry_counter += 1

        # Change state to Idle
        self.change_state("Idle")

    else:

        # Send the NOTIFICATION with the Error Code Finite State Machine Error
        await self.notification_message(FiniteStateMachineError)

        # Set Connect RetryTimer to zro
        self.connect_retry_timer = 0

        # Increment the ConnectRetryCounter by 1
        self.connect_retry_counter += 1

        self.change_state("Idle")
