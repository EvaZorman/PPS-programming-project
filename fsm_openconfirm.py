# import messages
from errors import FiniteStateMachineError

# From Sam


async def fsm_openconfirm(self, event):
    """Openconfirm state"""

    if event.name == "Event 11: KeepaliveTimer_Expires":
        self.logger.info(event.name)

        # Send KEEPALIVE message
        await self.send_keepalive_message()

        # Restart the KeepaliveTimer
        self.keepalive_timer = self.keepalive_time

    """
    Event 18: TcpConnectionFails
    Definition: Should be called when the associated TCP connection failed,
                or was lost.
    Status: Mandatory
    """

    if event.name == "Event 18: TcpConnectionFails":
        self.logger.info(event.name)

        # Increment the ConnectRetryCounter by 1
        self.connect_retry_counter += 1

        # Change state to Idle
        self.change_state("Idle")

    if event.name in {"Event 21: BGPHeaderErr", "Event 22: BGPOpenMsgErr"}:
        self.logger.info(event.name)

        # From Sam
        message = event.errors

        # Send a NOTIFICATION message with the appropriate error code
        await self.notification_message(
            message.message_error_code, message.message_error_subcode
        )

        # Increment ConnectRetryCounter
        self.connect_retry_counter += 1

        # Change state to Idle
        self.change_state("Idle")

    """
    Event 26: KeepAliveMsg
    Definition: Should be called when a BGP KeepAlive packet
                was received from the peer.
    Status: Mandatory
    """

    if event.name == "Event 26: KeepAliveMsg":
        self.logger.info(event.name)

        # Restart the HoldTimer
        self.hold_timer = self.hold_time

        # Change state to Established
        self.change_state("Established")

    else:

        # Send the NOTIFICATION with the Error Code Finite State Machine Error
        await self.notification_message(FiniteStateMachineError)

        # Increment the ConnectRetryCounter by 1
        self.connect_retry_counter += 1

        self.change_state("Idle")
