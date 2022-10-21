import ipaddress
import struct
from enum import Enum

from errors import NotificationMessage


class Message(Enum):
    OPEN = 1
    UPDATE = 2
    NOTIFICATION = 3
    KEEPALIVE = 4


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

    def __init__(self, msg_length: int = None):
        self.version = 4
        self.max_length = 4096

        #  Need to be set for each BGP message accordingly
        self.msg_type = None
        self.min_length = 19

        # create the basic BGP header
        self.marker = b"\xff" * 16
        if not msg_length:
            self.msg_length = 19
        else:
            self.msg_length = msg_length
        self.msg_type = None

    def verify_header(self):
        if self.msg_length < self.min_length:
            # "msg=Message is less than minimum length") #links up with error file
            raise NotificationMessage((3, 1))

        # only extract the 19 bytes of the BGP header data
        if self.marker != b"\xff" * 16:
            raise NotificationMessage((0, 1))

        if self.msg_length < self.min_length or self.msg_length > self.max_length:
            raise NotificationMessage((0, 2))  # Bad Message Length

        # todo: whazdis?
        # if len(data) < _msg_length:
        #    raise NotificationMessage(0, 2)  # bad message length

        if self.msg_type not in Message:
            raise NotificationMessage((0, 3))  # Bad Message Type


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

    def __init__(self, withdrawn_routes_len, withdrawn_routes, total_pa_len, total_pa, nlri):
        super().__init__()
        self.message_type = Message.UPDATE
        self.min_length = 23  # bytes

        # A tuple of:
        # +---------------------------+
        # |   Length (1 octet)        | - length in bits of the IP addr. prefix
        # +---------------------------+
        # |   Prefix (variable)       | - IP addr. prefix, padding
        # +---------------------------+
        self.withdrawn_routes = withdrawn_routes
        self.withdrawn_routes_len = withdrawn_routes_len

        # Each path attribute is a triple of:
        # (attribute type, attribute length, attribute value)

        # Attribute type is a tuple of:
        # 0                   1
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |  Attr. Flags  |Attr. Type Code|
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        self.total_pa = total_pa
        self.total_pa_len = total_pa_len

        self.nlri = nlri

    def verify(self):
        self.verify_header()
        if self.withdrawn_routes_len == 0 and self.withdrawn_routes:
            raise NotificationMessage((2, 1))  # Malformed Attribute List

        if self.total_pa_len == 0 and (self.nlri or self.total_pa):
            raise NotificationMessage((2, 1))  # Malformed Attribute List

        # TODO: lotsa work to be done...

    def extract_header(self, data, msg_len, capability):
        msg_result = dict()

        withdrawn_length = struct.unpack("!H", data[:2])[0]
        withdrawn_routes = data[2: withdrawn_length + 2]
        self.extract_header(withdrawn_routes, capability.get("add path"))

        attribute_length = struct.unpack(
            "!H", data[withdrawn_length + 2: withdrawn_length + 4]
        )
        attr_data = data[withdrawn_length + 4: withdrawn_length + 4 + attribute_length]
        nlri_data = data[withdrawn_length + 4 + attribute_length]
        msg_result["nlri"] = self.extract_nlri(nlri_data, capability.get("add path"))

        return msg_result, msg_len

    @staticmethod
    def extract_nlri(data, add_path):
        """
        Network Layer Reachability Information (variable)
        This variable length field contains a list of IP address prefixes.

        The minimum length of the UPDATE message is 23 bytes -- 19 bytes
        for the fixed header + 2 bytes for the Withdrawn Routes Length + 2
        """
        prefixes = []
        postfix = data

        while data.extract_nlri(postfix) > 0:
            if add_path:
                path_id = struct.unpack("!I", postfix[0:4])[0]
                postfix = postfix[4:]
            if isinstance(postfix[0], int):
                prefix_length = postfix[0]
            else:
                prefix_length = ord(postfix[0:1])
            if prefix_length > 32:
                raise NotificationMessage(3, 2)  # Prefix Length larger than 32
            octet_length, remainder = int(prefix_length / 8), prefix_length % 8
            # if the prefix length is not in octet
            if remainder > 0:
                octet_length += 1
            tmp = postfix[1: octet_length + 1]
            if isinstance(postfix[0], int):
                prefix_data = [i for i in tmp]
            else:
                prefix_data = [ord(i[0:1]) for i in tmp]

            # if prefix length is in octet
            if remainder > 0:
                prefix_data[-1] &= 255 << (8 - remainder)
            prefix_data = prefix_data + list(str(0)) * 4
            prefix = (
                    "%s.%s.%s.%s" % (tuple(prefix_data[0:4])) + "/" + str(prefix_length)
            )
            if not add_path:
                prefixes.append(prefix)
            else:
                prefixes.append({"prefix": prefix, "path_id": path_id})

            postfix = postfix[octet_length + 1:]

        return prefixes

    def compress_nlri(self, nlri, add_path=False):
        # prefix list for Network Layer Reachability Information (variable)
        nlri_raw_hex = b""
        for prefix in nlri:
            if add_path and isinstance(prefix, dict):
                path_id = prefix.get("path_id")
                prefix = prefix.get("prefix")
                nlri_raw_hex += struct.pack("!I", path_id)
            ip, mask_length = prefix.split("/")
            # ip_hex = ipaddress class # to be fixed once i see where the ip class
            mask_length = int(mask_length)
            if 16 < mask_length <= 24:
                ip_hex = ip_hex[0:3]
            elif 8 < mask_length <= 16:
                ip_hex = ip_hex[0:2]
            elif mask_length <= 8:
                ip_hex = ip_hex[0:1]
            nlri_raw_hex += struct.pack("!B", mask_length) + ip_hex
        return nlri_raw_hex


class KeepAliveMessage(BGPMessage):
    """
    A KEEPALIVE message consists of only the message header and has a
    length of 19 bytes.
    """

    def __init__(self):
        super().__init__()
        self.message_type = Message.KEEPALIVE

    def verify(self):
        self.verify_header()


class OpenMessage(BGPMessage):
    """"
    After a TCP connection is established, the first message sent by each
    side is an OPEN message.
    https://www.rfc-editor.org/rfc/rfc4271.html

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
    | Opt Parm Len  |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    |             Optional Parameters (variable)                    |
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    """

    def __init__(self, as_number, hold_time, bgp_id, param_len=0, params=None):
        super().__init__()
        self.message_type = Message.OPEN
        self.min_length = 29  # bytes

        self.as_number = as_number
        self.hold_time = hold_time
        self.bgp_id = bgp_id
        self.param_len = param_len
        # 0                   1
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...
        # |  Parm. Type   | Parm. Length  |  Parameter Value (variable)
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...
        self.params = params

    def verify(self):
        self.verify_header()
        if self.version != 4:
            raise NotificationMessage((1, 1))  # Unsupported version number

        if self.as_number == 0:
            raise NotificationMessage((1, 2))  # Bad Peer AS

        if self.hold_time < 3 or self.hold_time == 0:
            raise NotificationMessage((1, 6))  # Unacceptable Hold Time

        try:
            ipaddress.IPv4Address(self.bgp_id)
        except ipaddress.AddressValueError as e:
            raise NotificationMessage((1, 3)) from e  # Bad BGP Identifier

        if not self.param_len and self.params:
            raise NotificationMessage((1, 4))  # Unsupported Optional Parameter
