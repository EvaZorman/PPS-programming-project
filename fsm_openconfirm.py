from errors import FiniteStateMachineError
from state_machine import State


async def fsm_openconfirm(cls, event):
    """Openconfirm state"""

    if event.get_name() == "Event 11: KeepaliveTimer_Expires":
        cls.logger.info(event.get_name())

        # Send KEEPALIVE message
        await cls.send_keepalive_message()

        # Restart the KeepaliveTimer
        cls.keepalive_timer = cls.keepalive_time

    """
    Event 18: TcpConnectionFails
    Definition: Should be called when the associated TCP connection failed,
                or was lost.
    Status: Mandatory
    """
    if event.get_name() == "Event 18: TcpConnectionFails":
        cls.logger.info(event.get_name())

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1

        # Change state to Idle
        cls.change_state(State.IDLE)

    if event.get_name() in {"Event 21: BGPHeaderErr", "Event 22: BGPOpenMsgErr"}:
        cls.logger.info(event.get_name())

        # From Sam
        # TODO ?
        message = event.errors

        # Send a NOTIFICATION message with the appropriate error code
        await cls.notification_message(
            message.message_error_code, message.message_error_subcode
        )

        # Increment ConnectRetryCounter
        cls.connect_retry_counter += 1

        # Change state to Idle
        cls.change_state(State.IDLE)

    """
    Event 26: KeepAliveMsg
    Definition: Should be called when a BGP KeepAlive packet
                was received from the peer.
    Status: Mandatory
    """
    if event.get_name() == "Event 26: KeepAliveMsg":
        cls.logger.info(event.get_name())

        # Restart the HoldTimer
        cls.hold_timer = cls.hold_time

        # Change state to Established
        cls.change_state(State.ESTABLISHED)

    else:
        # Send the NOTIFICATION with the Error Code Finite State Machine Error
        await cls.notification_message(FiniteStateMachineError)

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1

        cls.change_state(State.IDLE)
