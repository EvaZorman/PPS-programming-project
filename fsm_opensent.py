from errors import FiniteStateMachineError
from state_machine import State


async def fsm_opensent(cls, event):
    """Opensent state"""

    if event.get_name() == "Event 18: TcpConnectionFails":
        cls.logger.info(event.get_name())

        # Close the TCP connection
        # cls.close_connection()

        # Restart the ConnectRetryTimer
        cls.connect_retry_timer = cls.connect_retry_time

        # Change state to Active
        cls.change_state(State.ACTIVE)

    """
           Event 19: BGPOpen
           Definition: Should be called when a BGP Open message was
                       received from the peer.
           Status: Mandatory
    """
    if event.get_name() == "Event 19: BGPOpen":

        cls.logger.info(event.get_name())

        message = event.message

        # Set the BGP ConnectRetryTimer to zero
        cls.connect_retry_timer = 0

        # Send a KeepAlive message
        await cls.send_keepalive_message()

        # I selected a Random value
        cls.hold_time = 60

        # Set a KeepAliveTimer
        cls.keepalive_time = cls.hold_time
        cls.keepalive_timer = cls.keepalive_time

        # Change state to OpenConfirm
        cls.change_state(State.OPEN_CONFIRM)

    if event.get_name() in {"Event 21: BGPHeaderErr", "Event 22: BGPOpenMsgErr"}:
        cls.logger.info(event.get_name())

        message = event.message

        # Send a NOTIFICATION message with the appropriate error code
        await cls.notification_message(
            message.message_error_code, message.message_error_subcode
        )

        # Increment ConnectRetryCounter
        cls.connect_retry_counter += 1

        # Change state to Idle
        cls.change_state(State.IDLE)

    else:
        # Send the NOTIFICATION with the Error Code Finite State Machine Error
        await cls.notification_message(FiniteStateMachineError)

        # Set Connect RetryTimer to zro
        cls.connect_retry_timer = 0

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1

        cls.change_state(State.IDLE)
