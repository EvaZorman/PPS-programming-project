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
import struct

from messages import (
    BGPMessage,
    NotificationMessage, Message
)


class OpenMessage(BGPMessage):
    def __init__(self, maker_):
        super().__init__(maker_)
        self.message_type = Message.OPEN
        self.version = 4

    def extract_header(self, data, msg_len, capability):
        open_msg = {}
        try:
            (
                open_msg["version"],
                open_msg["as_num"],
                open_msg["hold-time"],
            ) = struct.unpack(
                "!BHH", data[:5]
            )  # B - unsigned char, H - unsigned short, h - short
        except Exception as ex:
            raise NotificationMessage(0, 2) from ex  # Bad Message Length

        if open_msg["version"] != self.version:
            raise NotificationMessage(1, 1)  # Unsupported Version Number

        if open_msg["as_num"] == 0:
            raise NotificationMessage(1, 2)  # Bad Peer AS

        if isinstance(open_msg["as_num"], float):
            tmp = str(open_msg["as_num"]).split(".")
            open_msg["as_num"] = 65536 * (int(tmp[0])) + int(tmp[1])

        try:
            # open_msg['bgp_id'] = possible_ipaddress.unpack(data[5:9]
            pass
        except Exception as ex:
            raise NotificationMessage(1, 3) from ex  # Bad BGP Identifier

        # opt_para_len = struct.unpack('!B', data[9:10])  # B - unsigned char, H - unsigned short, h - short
        # if opt_para_len:
        #     open_msg['capabilities']
