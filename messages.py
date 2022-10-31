import ipaddress
from enum import Enum


class Message(Enum):
    MESSAGE = 0
    OPEN = 1
    UPDATE = 2
    NOTIFICATION = 3
    KEEPALIVE = 4
    TRUSTRATE = 5
    VOTING = 6


class BGPMessage:
    """
    BGP Message classes and functionality.

    This part will handle the BGP Messages structure, etc.
    See https://www.iana.org/assignments/bgp-parameters/bgp-parameters.xhtml#bgp-parameters-3

    https://www.rfc-editor.org/rfc/rfc4271.html

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    +                                                               +
    |                           Marker                              |
    +                                                               +
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Length               |      Type     |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    General BGP messages need to provide us with the following functionality:
        1. generate the BGP header
        2. be able to verify the header
    """

    def __init__(self, router_number, msg_length: int = None):
        self.version = 4
        self.max_length = 4096

        #  Need to be set for each BGP message accordingly
        self.msg_type = Message.MESSAGE
        self.min_length = 19

        # create the basic BGP header
        self.marker = b"\xff" * 16
        if not msg_length:
            self.msg_length = 19
        else:
            self.msg_length = msg_length

        self.router_number = router_number

    def __str__(self):
        return self.msg_type.name

    def get_message_type(self):
        return self.msg_type

    def get_sender(self):
        return self.router_number

    def verify_header(self):
        if self.msg_length < self.min_length:
            # "msg=Message is less than minimum length") #links up with error file
            raise NotificationMessage(self.router_number, (3, 1))

        # only extract the 19 bytes of the BGP header data
        if self.marker != b"\xff" * 16:
            raise NotificationMessage(self.router_number, (0, 1))

        if self.msg_length < self.min_length or self.msg_length > self.max_length:
            raise NotificationMessage(self.router_number, (0, 2))  # Bad Message Length

        if self.msg_type not in Message:
            raise NotificationMessage(self.router_number, (0, 3))  # Bad Message Type

    def verify(self):
        return self.verify_header()


class UpdateMessage(BGPMessage):
    """
    +-----------------------------------------------------+
    |   Withdrawn Routes Length (2 bytes)                 |
    +-----------------------------------------------------+
    |   Withdrawn Routes (variable)                       |
    +-----------------------------------------------------+
    |   Total Path Attribute Length (2 bytes)             |
    +-----------------------------------------------------+
    |   Path Attributes (variable)                        |
    +-----------------------------------------------------+
    |   Network Layer Reachability Information (variable) |
    +-----------------------------------------------------+

    Update messages need to provide us with the following functionality:
        1. Generate an update message with a passed list of route changes
        2. Extract any route changes from the update message
        3. Verify the update message contents
    """

    def __init__(
        self,
        router_number,
        withdrawn_routes_len=0,
        withdrawn_routes=None,
        total_pa_len=0,
        total_pa=None,
        nlri=None,
    ):
        super().__init__(router_number, 23 + withdrawn_routes_len + total_pa_len)
        self.msg_type = Message.UPDATE
        self.min_length = 23  # bytes

        self.withdrawn_routes = withdrawn_routes  # [ip-prefix, ...]
        self.withdrawn_routes_len = withdrawn_routes_len  # "2 bytes" in size

        # Note that we are ignoring the BGP RFC-4271 to make these easier to implement
        # and are using only a small subset of path attributes in the UPDATE messages
        self.total_pa = total_pa  # {attr. type: attr. value, ...}
        self.total_pa_len = total_pa_len  # "2 bytes" in size
        self.possible_attributes = {
            "ORIGIN",
            "NEXT_HOP",
            "LOCAL_PREF",
            "WEIGHT",
            "AS_PATH",
        }

        # UPDATE message Length - 23 - Total Path Attributes Length - Withdrawn Routes Length
        # path attributes advertised apply for the prefixes found in the NLRI
        self.nlri = nlri  # [ip-prefix, ...]

    def verify(self):
        self.verify_header()
        if self.withdrawn_routes_len == 0 and self.withdrawn_routes:
            raise NotificationMessage(
                self.router_number, (2, 1)
            )  # Malformed Attribute List

        if self.total_pa_len == 0 and (self.nlri or self.total_pa):
            raise NotificationMessage(
                self.router_number, (2, 1)
            )  # Malformed Attribute List

    def get_nlri(self):
        return self.nlri

    def get_path_attr(self):
        return self.total_pa


class KeepAliveMessage(BGPMessage):
    """
    A KEEPALIVE message consists of only the message header and has a
    length of 19 bytes.
    """

    def __init__(self, router_number):
        super().__init__(router_number)
        self.msg_type = Message.KEEPALIVE

    def verify(self):
        self.verify_header()


class OpenMessage(BGPMessage):
    """ "
    After a TCP connection is established, the first message sent by each
    side is an OPEN message.
    https://www.rfc-editor.org/rfc/rfc4271.html

    Note that we are ignoring optional parameters and will not be using them
    within the scope of this simulation.

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+
    |    Version    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |     My Autonomous System      |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Hold Time           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                         BGP Identifier                        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """

    def __init__(self, router_number, bgp_id, hold_time=30):
        super().__init__(router_number, 29)
        self.msg_type = Message.OPEN
        self.min_length = 29  # bytes

        self.hold_time = hold_time
        self.bgp_id = bgp_id

    def verify(self):
        self.verify_header()
        if self.version != 4:
            raise NotificationMessage(
                self.router_number, (1, 1)
            )  # Unsupported version number

        if int(self.router_number) < 0:
            raise NotificationMessage(self.router_number, (1, 2))  # Bad Peer AS

        if self.hold_time > 100 or self.hold_time == 0:
            raise NotificationMessage(
                self.router_number, (1, 6)
            )  # Unacceptable Hold Time

        try:
            ipaddress.IPv4Address(self.bgp_id)
        except ipaddress.AddressValueError as e:
            raise NotificationMessage(
                self.router_number, (1, 3)
            ) from e  # Bad BGP Identifier


class TrustRateMessage(BGPMessage):
    """
            0                   1                   2
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Trust value          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           AS path             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    The TrustRate message will be exchanged periodically only to keep the
    trust rates up. Inherent trust will be set to a random value between 0.45 and
    0.55 by default, and trust will be changed for every 15 messages received. If
    there is no problem with the peer, the observed trust will raise for 0.1 after
    every 15 messages exchanged.

    The Trust value will be a combination of observed and inherent trust, since we
    want to simplify this simulation. This can easily be changed later on if needed.
    """

    def __init__(self, router_number, as_num, trust_value):
        super().__init__(router_number, 23)
        self.msg_type = Message.TRUSTRATE
        self.min_length = 23

        self.as_num = as_num
        self.trust_value = trust_value

    def verify(self):
        self.verify_header()

    def get_as_num(self):
        return self.as_num

    def get_trust_value(self):
        return self.trust_value


class VotingMessage(BGPMessage):
    """
        0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |               TTL             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |    Q or A     | Num. of peers |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |             Origin            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |        Peer in question       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Vote value          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    We decided to make the Voting message similar to the Open message.
    The Voting message will contain the "TTL" value which will tell the
    receiving parties who needs to answer and who doesn't.

    TTL - will originally always be set to 1, any party that receives the message
    checks its value, if it equals to 0, it is the 2nd neighbour and must answer the
    query

    Answer - if set to 0, it means it is requesting a vote, if set to 1, it is an
    answer to a voting query

    Origin - the AS/router that is asking the q

    Peer in question - the peer the router must vote for

    Vote value - the value of the vote a router provides for the query

    Once a router receives a voting message with the TTL value 0, it returns it
    to the peer in question, which forwards it to the origin. The origin updates its
    routing table with the new information.
    """

    def __init__(
        self, router_number, origin, q_or_a, peer_in_question, vote_value=None
    ):
        super().__init__(router_number, 29)
        self.msg_type = Message.VOTING
        self.voting_type = q_or_a
        self.num_of_2nd_neighbours = 0
        self.ttl = 2
        self.origin = origin
        self.peer_in_question = peer_in_question
        self.vote_value = vote_value

        self.min_length = 19 + 10  # bytes

    def verify(self):
        self.verify_header()

        if int(self.origin) < 0:
            raise NotificationMessage(self.router_number, (1, 2))  # Bad Peer AS

        if self.voting_type not in [0, 1]:
            raise NotificationMessage(self.router_number, (0, 3))  # Bad message type

        self.ttl -= 1

    def get_peer_to_vote_for(self):
        return self.peer_in_question

    def set_num_of_2nd_neighbours(self, value):
        self.num_of_2nd_neighbours = value

    def get_num_of_2nd_neighbours(self):
        return self.num_of_2nd_neighbours

    def get_origin(self):
        return self.origin

    def get_vote_value(self):
        return self.vote_value

    def is_answer(self):
        return self.voting_type

    def is_at_2nd_point(self):
        return self.ttl == 0


class NotificationMessage(BGPMessage, Exception):
    """ "
    https://www.rfc-editor.org/rfc/rfc4271.html
    These notification messages will be thrown when an error is detected
    while processing BGP messages.

    In addition to the fixed-size BGP header, the NOTIFICATION message
    contains the following fields:

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    | Error code    | Error subcode |   Data (variable)             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """

    def __init__(self, router_number, error_subcode):
        super().__init__(router_number, 21)
        self.msg_type = Message.NOTIFICATION
        self.min_length = 21  # octets

    error_code = {
        1: "Message Header Error",
        2: "OPEN Message Error",
        3: "UPDATE Message Error",
        4: "Hold Timer Expired",
        5: "Finite State Machine Error",
        6: "Cease",
    }

    # Message Header Error subcodes
    error_sub_code = {
        (0, 0): "Unknown error",
        (0, 1): "Connection Not Synchronized",
        (0, 2): "Bad Message Length",
        (0, 3): "Bad Message Type",
        # OPEN Message Error subcodes
        (1, 1): "Unsupported Version Number",
        (1, 2): "Bad Peer AS",
        (1, 3): "Bad BGP Identifier",
        (1, 4): "Unsupported Optional Parameter",
        (1, 5): "Deprecated",
        (1, 6): "Unacceptable Hold Time",
        # UPDATE Message Error subcodes
        (2, 1): "Malformed Attribute List",
        (2, 2): "Unrecognized Well-known Attribute",
        (2, 3): "Missing Well-known Attribute",
        (2, 4): "Attribute Flags Error",
        (2, 5): "Attribute Length Error",
        (2, 6): "Invalid ORIGIN Attribute",
        (2, 7): "Invalid NEXT_HOP Attribute",
        (2, 8): "Optional Attribute Error",
        (2, 9): "Invalid Network Field",
        (2, 10): "Invalid Network Field",
        (2, 11): "Malformed AS_PATH",
        # uncompleted message errors
        (3, 1): "The message is uncompleted or the rest hasn't arrived yet",
        (3, 2): "Prefix Length larger than 32",
    }


class FiniteStateMachineError(Exception):
    # BGP Finite State
    #    Machine Error
    error_code = {
        0: "Unspecified Error",
        1: "Receive Unexpected Message in OpenSent State",
        2: "Receive Unexpected Message in OpenSent State",
        3: "Receive Unexpected Message in Established State",
    }
