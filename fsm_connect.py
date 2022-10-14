import loguru

from state_machine import State


async def fsm_connect(cls, event):
    """Connect state"""
    """
        Event 2: ManualStop
        Definition: Should be called when a BGP ManualStop event is requested.
        Status: Mandatory
        """
    if event.get_name() == "Event 2: ManualStop":
        cls.logger.info(event.get_name())

        # Set ConnectRetryCounter to zero
        cls.connect_retry_counter = 0

        # Change state to Idle
        cls.change_state(State.IDLE)

    """
    Event 9: ConnectRetryTimer_Expires
    Definition: Called when the ConnectRetryTimer expires.
    Status: Mandatory
    """
    if event.get_name() == "Event 9: ConnectRetryTimer_Expires":
        cls.logger.info(event.get_name())

        # Restart the ConnectRetryTimer
        cls.connect_retry_timer = cls.connect_retry_time

        # Initiate a TCP connection to the other BGP peer
        # this is again router stuff

        # cls.task_set_connection = asyncio.create_task(cls.set_connection())
        # await asyncio.sleep(0.001)

        # Restart the ConnectRetryTimer
        cls.connect_retry_timer = cls.connect_retry_time

    """
    Event 16: Tcp_CR_Acked
    Event 17: TcpConnectionConfirmed
    Definition: Should be called when a TCP connection has successfully been
                established with the peer.
    Status: Mandatory
    """
    if event.get_name() in {"Event 16: Tcp_CR_Acked", "Event 17: TcpConnectionConfirmed"}:
        # Take an ownership of the connection
        cls.reader = event.get_reader()
        cls.writer = event.get_writer()
        cls.peer_ip = event.get_peer_ip()
        cls.peer_port = event.get_peer_port()
        cls.tcp_connection_established = True

        cls.logger = loguru.logger.bind(
            peer=f"{cls.mode} {cls.peer_ip}:{cls.peer_port}", state=cls.state
        )

        cls.logger.info(event.get_name())

        # Stop the ConnectRetryTimer and set the ConnectRetryTimer to zero
        cls.connect_retry_timer = 0

        # Send an open message to the peer
        await cls.send_open_message()

        # Set the hold_timer to a large value, hold_timer value of 4 minutes is suggested
        cls.hold_timer = 240

        # Changes state to OpenSent
        cls.change_state(State.OPEN_SENT)

    else:
        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1

        cls.change_state(State.IDLE)
