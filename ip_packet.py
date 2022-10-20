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
    1. Fragmentation - won't do!
    2. Check TTL if > 0 -> discard
    2. Decrease TTL value
    3. Checksum update
        ? Incremental update - we should do it
"""


def generate():
    # get whole header - the checksum field
    # split into 16 bit words
    # calculate 2's compliment
    # sum the words and remainders
    # 1's compliment
    # store the new checksum
    pass


def validate():
    # get whole header - with checksum field
    # split into 16 bit words
    # calculate 2's compliment
    # sum the words and remainders
    # check if the result equals to all 1's or 0xFFFF
    pass
