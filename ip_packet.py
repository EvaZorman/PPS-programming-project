"""
IP Packet

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |Version|  IHL  |Type of Service|          Total Length         |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |         Identification        |Flags|      Fragment Offset    |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |  Time to Live |    Protocol   |         Header Checksum       |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                       Source Address                          |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Destination Address                        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Options (Optional)                         |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                        Payload                                |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Steps to take when an IP package is received:
1. Header validation:
    1. Check link layer length >= 20 bytes
    2. Checksum correct?
    3. Check version number == 4
    4. Check if IHL field >= 5
    5. Check if total field length == IHL * 4
2. Local delivery decision
    1. Check the destination address, if it matches, you're done
3. Determine next hop
    1. Compare neighbour router IP addresses to the destination address
    2. Check if the prefix we're advertising is a match
    3. Examine the routing table and make a choice
4. Forward the packet
    2. Check TTL if > 0 -> discard
    2. Decrease TTL value
    3. Checksum update
"""
import ipaddress

from bitstring import BitArray


class IPPacket:
    def __init__(
        self, packet_size, ip_header_length, ttl, source_addr, destination_addr, payload
    ):
        # Header data
        self.version = 4  # 4 bits
        self.hl = ip_header_length  # 4 bits
        self.type_of_service = 0  # 8 bits
        self.total_length = packet_size  # 16 bits
        self.identification = 0  # 16 bits
        self.fragment_flags = "010"  # 3 bits
        self.fragment_offset = 0  # 13 bits
        self.ttl = ttl  # 8 bit
        self.protocol = 3  # 8 bits, see: https://www.rfc-editor.org/rfc/rfc790
        self.header_checksum = ""  # 16 bits
        self.source_addr = source_addr  # 32 bits
        self.destination_addr = destination_addr  # 32 bits

        # Payload data
        self.payload = payload

    def validate(self):
        # Header validation
        if (
            self.total_length < 20
            or not self.valid_checksum()
            or self.version != 4
            or self.hl < 5
            or self.total_length < self.hl * 4
        ):
            return False

        return True

    def generate_new_checksum(self):
        # get whole header - the checksum field
        # split into 16 bit words
        # calculate 2's compliment
        # sum the words and remainders
        # 1's compliment
        # store the new checksum

        # splitting the message into bits
        octet_1 = self.header_checksum[0:8]
        octet_2 = self.header_checksum[8:16]
        octet_3 = self.header_checksum[16:24]
        octet_4 = self.header_checksum[24:32]

        # sum packets in binary
        total = bin(octet_1 + octet_2 + octet_3 + octet_4)[2:]

        # Adding overflow bits
        if len(total) > 8:
            x = len(total) - 8
            total = bin(int(total[0:x]) + int(total[8:x]))[2:]
        if len(total) < 8:
            total = "0" * (8 - len(total)) + total

        # calculating complement of sum
        new_checksum = ""
        for i in total:
            if i == "1":
                new_checksum += "0"
            else:
                new_checksum += "1"
        return new_checksum

    def valid_checksum(self):
        # get whole header - with checksum field
        # split into 16 bit words
        # calculate 2's compliment
        # sum the words and remainders
        # check if the result equals to all 1's or 0xFFFF

        # splitting the message into bits
        octet_1 = self.header_checksum[0:8]
        octet_2 = self.header_checksum[8:16]
        octet_3 = self.header_checksum[16:24]
        octet_4 = self.header_checksum[24:32]

        # sum packets in binary
        received_total = bin(octet_1 + octet_2 + octet_3 + octet_4)[2:]

        if len(received_total) > 8:
            x = len(received_total) - 8
            received_total = bin(int(received_total[0:x]) + int(received_total[x:]))[2:]

        # calculating complement of sum
        received_checksum = ""
        for i in received_checksum:
            if i == "1":
                received_checksum += "0"
            else:
                received_checksum += "1"
        return received_checksum

    def to_data_link_layer_stream(self):
        """
        This function needs to covert the whole ip packet to 0's and 1's to
        send as a data link layer transfer to the router
        """
        data_link_stream = (
            BitArray(int=self.version, length=4).bin
            + BitArray(int=self.hl, length=4).bin
            + BitArray(int=self.type_of_service, length=8).bin
            + BitArray(int=self.total_length, length=16).bin
            + BitArray(int=self.identification, length=16).bin
            + self.fragment_flags
            + BitArray(int=self.fragment_offset, length=13).bin
            + BitArray(int=self.ttl, length=8).bin
            + BitArray(int=self.protocol, length=8).bin
            + BitArray(int=self.header_checksum, length=16).bin
            + BitArray(int=int(ipaddress.IPv4Address(self.source_addr)), length=32).bin
            + BitArray(
                int=int(ipaddress.IPv4Address(self.destination_addr)), length=32
            ).bin
            + BitArray(hex=self.payload.encode()).bin
        )

        return data_link_stream

    def get_destination_addr(self):
        return self.destination_addr
