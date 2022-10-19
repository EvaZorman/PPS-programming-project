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

class UpdateMessage(BGPMessage):
    TYPE = 2
    TYPE_STR = "UPDATE"

    def extract_header(self, data, msg_len, capability, attr_length=None):
        msg_result = dict()

        withdrawn_length = struct.unpack('!H', data[:2])[0]
        withdrawn_routes = data[2:withdrawn_length + 2]
        self.extract_header(withdrawn_routes, capability.get('add path'))

        attribute_length = struct.unpack('!H', data[withdrawn_length + 2:withdrawn_length + 4])
        attr_data = data[withdrawn_length + 4:withdrawn_length + 4 + attribute_length]
        nlri_data = data[withdrawn_length + 4 + attribute_length]
        msg_result['nlri'] = extract_nlri(nlri_data, capability.get('add path'))

        return msg_result, msg_len
'''
   Network Layer Reachability Information (variable)
   This variable length field contains a list of IP address prefixes.
   
    The minimum length of the UPDATE message is 23 octets -- 19 octets
   for the fixed header + 2 octets for the Withdrawn Routes Length + 2
'''


    def extract_nlri(data, add_path):
        prefixes = []
        postfix = data

        while len(postfix) > 0:
            if add_path:
                path_id = struct.unpack('!I', postfix[0:4])[0]
                postfix = postfix[4:]
            if isinstance(postfix[0], int):
                prefix_length = postfix[0]
            else:
                prefix_length = ord(postfix[0:1])
            if prefix_length > 32:
                raise NotificationMessage(3, 2) # Prefix Length larger than 32
            octet_length, remainder = int(prefix_length / 8), prefix_length % 8
            # if the prefix length is not in octet
            if remainder > 0:
                octet_length += 1
            tmp = postfix[1:octet_length + 1]
            if isinstance(postfix[0], int):
                prefix_data = [i for i in tmp]
            else:
                prefix_data = [ord(i[0:1]) for i in tmp]

            # if prefix length is in octet
            if remainder > 0:
                prefix_data[-1] &= 255 << (8 - remainder)
            prefix_data = prefix_data + list(str(0)) * 4
            prefix = "%s.%s.%s.%s" % (tuple(prefix_data[0:4])) + '/' + str(prefix_length)
            if not add_path:
                prefixes.append(prefix)
            else:
                prefixes.append({'prefix': prefix,  'path_id': path_id})

            postfix = postfix[octet_length + 1:]

        return prefixes

    def pack_msg_header(self, data, capability):
        pass

    def compress_nlri(nlri, add_path = False):
        '''
         prefix list for Network Layer Reachability Information (variable)
        '''
        nlri_raw_hex = b''
        for prefix in nlri:
            if add_path and isinstance(prefix, dict):
                path_id = prefix.get('path_id')
                prefix = prefix.get('prefix')
                nlri_raw_hex += struct.pack('!I', path_id)
            ip, mask_length = prefix.split('/')
           # ip_hex = ipaddress class # to be fixed once i see where the ip class
            mask_length = int(mask_length)
            if 16 < mask_length <= 24:
                ip_hex = ip_hex[0:3]
            elif 8 < mask_length <= 16:
                ip_hex = ip_hex[0:2]
            elif mask_length <= 8:
                ip_hex = ip_hex[0:1]
            nlri_raw_hex += struct.pack('!B', mask_length) + ip_hex
        return nlri_raw_hex
