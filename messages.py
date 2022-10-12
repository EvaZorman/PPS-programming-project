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
      |                                                               |
      +                                                               +
      |                           Marker                              |
      +                                                               +
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          Length               |      Type     |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

"""
import struct

from errors import NotificationMessage


class BGPMessage():
    buffer_ = ()
    marker = b"\xFF" * 16
    min_length = 19
    max_length = 4096
    received_message = {}
    TYPE = None
    # will be clearing below since they are declared in their respective classes
    OPEN = 1
    UPDATE = 2
    NOTIFICATION = 3
    KEEPALIVE = 4

    def __init__(self, maker_, msg_hex=None, msg_length=None):
        self.maker = maker_
        self.msg_hex = msg_hex
        self.msg_length = msg_length

    # BGPMessage.buffer_ = bytearray(maker_)

    """
    checks on  registered messages and 
    throws a runtime error
    """

    def write_marker(self, clas):
        if clas.TYPE in self.received_message:
            raise RuntimeError("message is a duplicate")
        self.received_message[clas.TYPE] = clas
        return clas

    def dict(self):
        return {"type": self.TYPE, "msg": self.maker}

    @staticmethod
    def header(msg_type, msg_body):
        return (
            BGPMessage.marker
            + struct.pack("!H", BGPMessage.min_length + len(msg_body))
            + struct.pack("!B", msg_type)
            + msg_body
        )

    def extract_header(self, data, msg_len, capability):
        if msg_len(data) < self.min_length:
            # "msg=Message is less than minimum length") #links up with error file
            raise NotificationMessage(3, 1)

        _marker, _msg_length, msg_type_ = struct.unpack("!16sHB", data[self.min_length])
        if _marker != self.marker:
            raise NotificationMessage(0, 1)

        if _msg_length < self.min_length or _msg_length > self.max_length:
            raise NotificationMessage(0, 2)  # Bad Message Length

        if len(data) < _msg_length:
            raise NotificationMessage(0, 2)  # bad message length

        if msg_type_ not in self.received_message:
            raise NotificationMessage(0, 3)  # Bad Message Type

        msg_body = data[self.min_length : _msg_length]
        clas = self.received_message[msg_body].extract_header(
            data=msg_body, _msg_length=msg_len, capability=capability
        )
        return clas

    def pack_msg_header(self, data, capability):
        msg_type = data.get("type")
        if msg_type not in self.received_message:
            raise NotificationMessage(0, 3)  # Bad Message Type
        msg_body = self.received_message[msg_type].pack_msg_header(
            data=data.get("msg"), capability=capability
        )
        # TODO fix this
        return BGPMessage(
            maker_=data.get("msg"), msg_hex=self.header(msg_type, msg_body.msg_hex)
        )


class KeepAliveMessage(BGPMessage):
    TYPE = 4
    TYPE_STR = "KEEPALIVE"

    def extract(self, data, msg_len, capab=None):
        if msg_len(data) != 0:
            raise NotificationMessage(1, 2)  # will need to throw error
        return BGPMessage(None, msg_length=msg_len + BGPMessage.min_length)
