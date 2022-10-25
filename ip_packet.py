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


def generate(packet):
    # get whole header - the checksum field
    # split into 16 bit words
    # calculate 2's compliment
    # sum the words and remainders
    # 1's compliment
    # store the new checksum

    # splitting the message into bits
    octet_1 = packet[0:8]
    octet_2 = packet[8:16]
    octet_3 = packet[16:24]
    octet_4 = packet[24:32]

    # sum packets in binary
    total = bin(octet_1 + octet_2 + octet_3 + octet_4)[2:]

    # Adding overflow bits
    if len(total) > 8:
        x = len(total) - 8
        total = bin(int(total[0:x]) + int(total[8:x]))[2:]
    if len(total) < 8:
        total = '0'*(8 - len(total)) + total

    # calculating complement of sum
    checksum = ''
    for i in total:
        if i == '1':
            checksum += '0'
        else:
            checksum += '1'
    return checksum


def validate(received_packet, checksum):
    # get whole header - with checksum field
    # split into 16 bit words
    # calculate 2's compliment
    # sum the words and remainders
    # check if the result equals to all 1's or 0xFFFF

    # splitting the message into bits
    octet_1 = received_packet[0:8]
    octet_2 = received_packet[8:16]
    octet_3 = received_packet[16:24]
    octet_4 = received_packet[24:32]

    # sum packets in binary
    received_total = bin(octet_1 + octet_2 + octet_3 + octet_4)[2:]

    if len(received_total) > 8:
        x = len(received_total) - 8
        received_total = bin(int(received_total[0:x]) + int(received_total[x:]))[2:]

    # calculating complement of sum
    received_checksum = ''
    for i in received_checksum:
        if i == '1':
            received_checksum += '0'
        else:
            received_checksum += '1'
    return received_checksum

# comparison will need to be made with the generated checksum



