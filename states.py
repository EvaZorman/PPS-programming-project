class State:
    """
    Possible states: IDLE, CONNECT, ACTIVE, OPEN_SENT,
    OPEN_CONFIRM, ESTABLISHED
    """

    def on_event(self, cls, event):
        pass

    def __str__(self):
        return self.__class__.__name__


class IdleState(State):
    def on_event(self, cls, event):
        if event.get_name() == "ManualStart":
            cls.connect_retry_counter = 0
            cls.connect_retry_timer = cls.connect_retry_time
            return ConnectState()

        return ActiveState()


class ConnectState(State):
    def on_event(self, cls, event):
        if event.get_name() == "ManualStop":
            cls.connect_retry_counter = 0
            return IdleState()
        if event.get_name() == "ConnectRetryTimer_Expires":
            cls.connect_retry_timer = cls.connect_retry_time
            return self
        if event.get_name() in {"Tcp_CR_Acked", "TcpConnectionConfirmed"}:
            # Stop the ConnectRetryTimer and set the ConnectRetryTimer to zero
            cls.connect_retry_timer = 0
            # Set the hold_timer to a large value, hold_timer value
            # of 4 minutes is suggested
            cls.hold_timer = 240
            return OpenSentState()

        cls.connect_retry_counter += 1
        return IdleState()


class ActiveState(State):
    def on_event(self, cls, event):
        if event.get_name() == "ManualStop":
            # Set ConnectRetryCounter to zero
            cls.connect_retry_counter = 0
            return IdleState()
        if event.get_name() == "ConnectRetryTimer_Expires":
            # Restart the ConnectRetryTimer
            cls.connect_retry_timer = cls.connect_retry_time
            # Stop KeepaliveTimer
            cls.keepalive_timer = 0
            return ConnectState()
        if event.get_name() in {"Tcp_CR_Acked", "TcpConnectionConfirmed"}:
            # Stop the ConnectRetryTimer and set the ConnectRetryTimer to zero
            cls.connect_retry_timer = 0
            # Set the hold_timer to a large value, hold_timer value
            # of 4 minutes is suggested
            cls.hold_timer = 240
            return OpenSentState()

        cls.connect_retry_counter += 1
        return IdleState()


class OpenSentState(State):
    def on_event(self, cls, event):
        if event.get_name() == "TcpConnectionFails":
            # Restart the ConnectRetryTimer
            cls.connect_retry_timer = cls.connect_retry_time
            return ActiveState()
        if event.get_name() == "BGPOpen":
            # Set the BGP ConnectRetryTimer to zero
            cls.connect_retry_timer = 0
            # I selected a Random value
            cls.hold_time = 60
            # Set a KeepAliveTimer
            cls.keepalive_time = cls.hold_time
            cls.keepalive_timer = cls.keepalive_time
            return OpenConfirmState()
        if event.get_name() in {"BGPHeaderErr", "BGPOpenMsgErr"}:
            message = event.message
            # Increment ConnectRetryCounter
            cls.connect_retry_counter += 1
            return IdleState()

        # Set Connect RetryTimer to zro
        cls.connect_retry_timer = 0
        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1
        return IdleState()


class OpenConfirmState(State):
    def on_event(self, cls, event):
        if event.get_name() == "KeepaliveTimer_Expires":
            # Restart the KeepaliveTimer
            cls.keepalive_timer = cls.keepalive_time
            return self
        if event.get_name() == "TcpConnectionFails":
            # Increment the ConnectRetryCounter by 1
            cls.connect_retry_counter += 1
            return IdleState()
        if event.get_name() in {"BGPHeaderErr", "BGPOpenMsgErr"}:
            # Increment ConnectRetryCounter
            cls.connect_retry_counter += 1
            return IdleState()
        if event.get_name() == "KeepAliveMsg":
            # Restart the HoldTimer
            cls.hold_timer = cls.hold_time
            return EstablishedState()

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1
        return IdleState()


class EstablishedState(State):
    def on_event(self, cls, event):
        if event.get_name() == "KeepaliveTimer_Expires":
            # Restart KeepaliveTimer
            cls.keepalive_timer = cls.keepalive_time
            return self

        # Increment the ConnectRetryCounter by 1
        cls.connect_retry_counter += 1
        return IdleState()
