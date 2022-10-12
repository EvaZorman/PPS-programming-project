import asyncio

import loguru


async def fsm_connect(self, event):
    """Connect state"""
    """
        Event 2: ManualStop
        Definition: Should be called when a BGP ManualStop event is requested.
        Status: Mandatory
        """

    if event.name == "Event 2: ManualStop":
        self.logger.info(event.name)

        # Set ConnectRetryCounter to zero
        self.connect_retry_counter = 0

        # Change state to Idle
        self.change_state("Idle")

    """
    Event 9: ConnectRetryTimer_Expires
    Definition: Called when the ConnectRetryTimer expires.
    Status: Mandatory
    """

    if event.name == "Event 9: ConnectRetryTimer_Expires":
        self.logger.info(event.name)

        # Restart the ConnectRetryTimer
        self.connect_retry_timer = self.connect_retry_time

        # Initiate a TCP connection to the other BGP peer
        self.task_set_connection = asyncio.create_task(self.set_connection())
        await asyncio.sleep(0.001)

        # Restart the ConnectRetryTimer
        self.connect_retry_timer = self.connect_retry_time

    """
    Event 16: Tcp_CR_Acked
    Event 17: TcpConnectionConfirmed
    Definition: Should be called when a TCP connection has successfully been
                established with the peer.
    Status: Mandatory
    """

    if event.name in {"Event 16: Tcp_CR_Acked", "Event 17: TcpConnectionConfirmed"}:
        # Take an ownership of the connection
        self.reader = event.reader
        self.writer = event.writer
        self.peer_ip = event.peer_ip
        self.peer_port = event.peer_port
        self.tcp_connection_established = True

        self.logger = loguru.logger.bind(
            peer=f"{self.mode} {self.peer_ip}:{self.peer_port}", state=self.state
        )

        self.logger.info(event.name)

        # Stop the ConnectRetryTimer and set the ConnectRetryTimer to zero
        self.connect_retry_timer = 0

        # Send an open message to the peer
        await self.send_open_message()

        # Set the hold_timer to a large value, hold_timer value of 4 minutes is suggested
        self.hold_timer = 240

        # Changes state to OpenSent
        self.change_state("OpenSent")

    else:
        # Increment the ConnectRetryCounter by 1
        self.connect_retry_counter += 1

        self.change_state("Idle")
