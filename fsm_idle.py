import asyncio


async def fsm_idle(self, event):
    """ Idle state """
    """
    Note: For now, we are not implementing all events only Mandatory One!!
    
    For example, if we try to implement all BGP events Then according to RFC4271 documentation 
    in "Idle" part there are 4 Events,
    Event 1: Manual Start
    Event 3: Automatic Start
    Event 4: Manual Start with Passive TCP Est
    Event 5: Automatic Start with Passive TCP EST
    
    Reference: https://www.rfc-editor.org/rfc/rfc4271#section-8.1
    """

    if event.name == "Event 1: ManualStart":

        """
        Event 1: ManualStart
        Definition: Should be called when a BGP ManualStart event is requested.
        Status: Mandatory
        """

        self.logger.info(event.name)

        # Sets ConnectRetryCounter to zero
        self.connect_retry_counter = 0

        # Starts the ConnectRetryTimer with the initial value
        self.connect_retry_timer = self.connect_retry_time

        # Initiate a TCP connection to the other BGP peer
        self.task_open_connection = asyncio.create_task(self.set_connection())

        # Listen for a connection that may be initiated by the remote BGP peer
        pass

        # Change state to Connect
        self.change_state("Connect")

    else:

        # Change state to Active
        self.change_state("Active")
