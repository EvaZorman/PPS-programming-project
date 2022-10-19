import asyncio


async def decrease_connect_retry_timer(cls):
    """Decrease connect_retry_timer every second if its value is greater than zero"""

    cls.logger.debug("Starting decrease_connect_retry_timer() coroutine")

    if not hasattr(cls, "connect_retry_timer"):
        cls.connect_retry_timer = 0

    while True:
        await asyncio.sleep(1)
        if cls.connect_retry_timer:
            cls.logger.debug(f"connect_retry_timer = {cls.connect_retry_timer}")
            cls.connect_retry_timer -= 1
            if not cls.connect_retry_timer:
                cls.enqueue_event("ConnectRetryTimer_Expires")


async def decrease_hold_timer(cls):
    """Decrease hold_timer every second if its value is greater than zero"""

    cls.logger.debug("Starting decrease_hold_timer() coroutine")

    if not hasattr(cls, "hold_timer"):
        cls.hold_timer = 0

    while True:
        await asyncio.sleep(1)
        if cls.hold_timer:
            cls.logger.debug(f"hold_timer = {cls.hold_timer}")
            cls.hold_timer -= 1
            if not cls.hold_timer:
                # create an event
                cls.enqueue_event("HoldTimer_Expires")


async def decrease_keepalive_timer(cls):
    """Decrease keepalive_timer every second if its value is greater than zero"""

    cls.logger.debug("Starting decrease_keepalive_timer() coroutine")

    if not hasattr(cls, "keepalive_timer"):
        cls.keepalive_timer = 0

    while True:
        await asyncio.sleep(1)
        if cls.keepalive_timer:
            cls.logger.debug(f"keepalive_timer = {cls.keepalive_timer}")
            cls.keepalive_timer -= 1
            if not cls.keepalive_timer:
                # create an event and pass
                cls.enqueue_event("KeepaliveTimer_Expires")
