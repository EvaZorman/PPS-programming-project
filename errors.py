""""
https://www.rfc-editor.org/rfc/rfc4271.html
In addition to the fixed-size BGP header, the NOTIFICATION message
   contains the following fields:

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      | Error code    | Error subcode |   Data (variable)             |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      These notification messages will be thrown when an error is detected while processing
      BGP messages.
"""
import struct

from messages import BGPMessage


class NotificationMessage(BGPMessage, Exception):
    TYPE = 3
    TYPE_STR = 'Notification'

    error_code = {
        1: "Message Header Error",
        2: "OPEN Message Error",
        3: "UPDATE Message Error",
        4: "Hold Timer Expired",
        5: "Finite State Machine Error",
        6: "Cease"
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
        (3, 1): "The message is uncompleted or the rest hasn't arrived yet"

    }

    # def extract_header(self, data, msg_len, capability):
    #     error, sub_error = struct.unpack('!BB', data[:2])
    #     if (error, sub_error) in self.error_sub_code:
    #         return self(
    #             maker={
    #                 'code': [error, sub_error],
    #                 'msg': self.error_sub_code[(error, sub_error)]
    #             },
    #             msg_len=msg_len
    #         )
    #     else:
    #         return self(maker='unknown error', msg_len=msg_len)
    #
    # def pack_msg_header(self, data, capability):
    #     msg = struct.pack("!BB", data['code'][1])
    #     return self(self.maker=data, msg_hex=msg)

