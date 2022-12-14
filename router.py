"""
use class BGP_router to create router objects.

I have used Multi Threading to run servers and clients concurrently.

steps:

1- use a loop to create 10 different objects with 10 different IPs. you can use list
interface_list to do so.

2- each needs to listen and accept a connection by calling the functions. to be put in the main function.

3- states are changed based on the content of messages. this part is left to Sam.
it should be done by looking into the RFCs related to BGP and based on what exist
in the headers in binary format.

4- should you have any question feel free to ask me anytime.
"""

import ipaddress
import logging
import os
import pickle
import random
import sched
import select
import socket
import threading
from time import sleep

import pandas

import states
from events import Event
from messages import (
    UpdateMessage,
    KeepAliveMessage,
    OpenMessage,
    FiniteStateMachineError,
    Message,
    VotingMessage,
    TrustRateMessage,
)
from state_machine import BGPStateMachine

BUFFER_SIZE = 1024  # Normally 1024
S_PRINT_LOCK = threading.Lock()

if os.environ.get("DEBUG_ON"):
    logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("BGP")


def s_print(*args, **kwargs):
    """
    Prints to console safely from multiple threads by making sure the
    lock is obtained.
    """
    with S_PRINT_LOCK:
        print(*args, **kwargs)


def get_random_trust_value():
    """
    Generate random values from the interval [0.45, 0.55]
    """
    r = random.Random()
    return r.randrange(45, 55) / 100


class Router:
    def __init__(self, name, ip, router_number, discovered_paths):
        self.name = name
        self.ip = ip

        # setup placeholders since multithreading is breaking us and no locks were properly implemented...
        self.bgp_setup_complete = False
        self.voting_setup_complete = False
        self.advertise_setup_complete = False

        self.sm = BGPStateMachine(f"SM-{name}", 5, discovered_paths)
        self.message_scheduler = sched.scheduler()

        self.paths = discovered_paths

        self.updates_received = 0

        self.trust_values = {peer: 0 for peer in discovered_paths}
        self.messages_exchanged = {peer: 0 for peer in discovered_paths}
        self.vote_values = {peer: [] for peer in discovered_paths}
        self.vote_complete = {peer: False for peer in discovered_paths}

        self.path_table = {
            "NETWORK": [],
            "NEXT_HOP": [],
            "MED": [],
            "LOC_PREF": [],
            "WEIGHT": [],
            "TRUST_RATE": [],
            "AS_PATH": [],
        }
        self.advetised_prefixes = set()

        self.stop_listening = threading.Event()

        # BGP receiving and listening sockets
        """
        This is ugly... port range will for now always be the router num
        multiplied by 4 (since we need 4 ports), in the range of:
            port: bgp_listener
            port + 1: bgp_speaker
            port + 2: data_listener
            port + 3: data_speaker
        """
        base_num = 2000 + 4 * router_number
        self.ports = [base_num, base_num + 1, base_num + 2, base_num + 3]

        self.listener = RouterListener(f"R{self.name}", self.ports[0], self.ports[2])
        self.speaker = RouterSpeaker(f"R{self.name}", self.ports[1], self.ports[3])

    def start(self, connections=50):
        # start listening
        self.listener.listen_bgp_socket.listen(connections)
        self.listener.listen_data_socket.listen(connections)

        read_list = [self.listener.listen_bgp_socket, self.listener.listen_data_socket]

        # start the while loop
        while not self.stop_listening.is_set():
            readable, writeable, errors = select.select(read_list, [], [], 0.5)
            for r in readable:
                if r is self.listener.listen_bgp_socket:
                    (
                        bgp_client_socket,
                        bgp_client_addr,
                    ) = self.listener.listen_bgp_socket.accept()
                    # extract the data
                    pickled_data = bgp_client_socket.recv(BUFFER_SIZE)
                    message = pickle.loads(pickled_data)

                    # handle the message based on internal state
                    self.handle_bgp_data(message)
                    bgp_client_socket.close()

                if r is self.listener.listen_data_socket:
                    (
                        data_client_socket,
                        data_client_addr,
                    ) = self.listener.listen_data_socket.accept()
                    # extract the data
                    pickled_data = data_client_socket.recv(BUFFER_SIZE)
                    message = pickle.loads(pickled_data)

                    # handle the message based on internal state
                    self.handle_data(message)
                    data_client_socket.close()

    def stop(self):
        self.stop_listening.set()

    def update_voting_value(self, peer, num_of_2nd_neighbours, voted_trust_value=None):
        if voted_trust_value:
            self.vote_values[peer].append(voted_trust_value)

        # check the number of 2nd neighbours a node has, and if the length of the votes array matches,
        # mark it as complete
        if num_of_2nd_neighbours == len(self.vote_values[peer]):
            self.vote_complete[peer] = True

        if all(self.vote_complete.values()):
            logger.debug(
                f"Router {self.name} vote value table: {self.vote_values}, number of 2nd neighbours: {num_of_2nd_neighbours}"
            )
            self.voting_setup_complete = True

        # if we have all the votes from the 2nd neighbours, update the new
        # trust value
        # if len(self.vote_values[peer]) == num_of_2nd_neighbours:
        #     # get index value of the peer
        #     index = self.path_table["AS_PATH"].index(str(peer))
        #     logger.debug(f"Got index for peer {peer} at: {index}")
        #
        #     voted_trust = 0
        #     for v in self.vote_values[peer]:
        #         voted_trust += v
        #     voted_trust = voted_trust / len(self.vote_values[peer])
        #
        #     # construt the new trust value
        #     self.path_table["TRUST_RATE"][index] = 1 / (
        #         0.4 * self.path_table["TRUST_RATE"][index]
        #     ) + (0.6 * (voted_trust / len(self.vote_values[peer])))
        #
        #     self.vote_values[peer].append(voted_trust_value)
        #     logger.debug(f"New voting table: {self.vote_values}")

    def get_trust_rate(self, peer):
        if not self.vote_values[peer]:
            return self.trust_values[peer]

        votes_mean = sum(self.vote_values[peer]) / len(self.vote_values[peer])
        return 1 / (0.4 * self.trust_values[peer]) + (0.6 * votes_mean)

    def distribute_trust_values(self, peer_list):
        for i in peer_list:
            # tell the other peers what is your trust value of chosen peer
            peers_to_distribute = list(peer_list)
            peers_to_distribute.remove(i)
            # get the trust value of the chosen peer
            trust_value = self.path_table["TRUST_RATE"][
                self.path_table["AS_PATH"].index(str(i))
            ]
            for peer in peers_to_distribute:
                # send all other peers the trust value and AS path of the chosen peer
                self.bgp_send(
                    peer, TrustRateMessage(self.name, trust_value, f"{self.name} {i}")
                )
                sleep(5)

    def get_routing_table_size(self):
        return len(self.path_table["MED"])

    def update_routing_table(self, data):
        pa = data.get_path_attr()
        nlri = data.get_nlri()

        for i in nlri:
            if self.name in pa["AS_PATH"]:
                return False

            self.path_table["NETWORK"].append(i)
            self.path_table["NEXT_HOP"].append(pa["NEXT_HOP"])
            self.path_table["MED"].append(pa["MED"])
            self.path_table["LOC_PREF"].append(pa["LOC_PREF"])
            self.path_table["WEIGHT"].append(pa["WEIGHT"])
            self.path_table["AS_PATH"].append(pa["AS_PATH"])

            # update the trust rate value
            if len(pa["AS_PATH"].split()) > 1:
                self.path_table["TRUST_RATE"].append(
                    pa["TRUST_RATE"]
                    + self.get_trust_rate(int(pa["AS_PATH"].split()[0]))
                )
            else:
                self.path_table["TRUST_RATE"].append(
                    self.get_trust_rate(int(pa["AS_PATH"]))
                )

        return True

    def customise_routing_table(self, row, choice, value):
        for c in choice:
            if c == "m":
                self.path_table["MED"][row] = value
            if c == "l":
                self.path_table["LOC_PREF"][row] = value
            if c == "w":
                self.path_table["WEIGHT"][row] = value
            if c == "t":
                self.path_table["TRUST_RATE"][row] = int(value)
            # self.print_routing_table()

    def print_routing_table(self):
        df = pandas.DataFrame(self.path_table)
        s_print(
            f"Routing table for router {self.name}: \n"
            f"{df.sort_values(by='NETWORK').to_string()} \n"
        )

    def remove_table_entry(self, row):
        del self.path_table["NETWORK"][row]
        del self.path_table["NEXT_HOP"][row]
        del self.path_table["MED"][row]
        del self.path_table["LOC_PREF"][row]
        del self.path_table["WEIGHT"][row]
        del self.path_table["TRUST_RATE"][row]
        del self.path_table["AS_PATH"][row]

    def determine_next_hop(self, ip_packet):
        """
        Figures out which is the best path and returns the next hop ip address.
        """
        # get all stored networks
        netw_addresses = list(set(self.path_table["NETWORK"]))
        # get the longest address match for the ip packet destination
        common_bits_list = []
        for addr in netw_addresses:
            common_bits_list.append(
                int(ipaddress.IPv4Address(ip_packet.get_destination_addr()))
                ^ int(ipaddress.ip_network(addr).network_address)
            )
        # as far as I can see, we can really only XOR easily in Python, so let's
        # XOR the addresses and the smallest value is the best match
        logger.debug(f"Common bits list for router {self.name}: {common_bits_list}")
        longest_addr_match = netw_addresses[
            common_bits_list.index(min(common_bits_list))
        ]

        # find all paths that lead to that destination
        possible_path_indexes = []
        for index, addr in enumerate(self.path_table["NETWORK"]):
            if addr != longest_addr_match:
                continue
            possible_path_indexes.append(index)

        # run the checks to find the best path
        best_path_index = self.find_best_path(possible_path_indexes)
        s_print(
            f"Found best possible path of: {self.path_table['AS_PATH'][best_path_index]}"
        )

        # return the next hop value for the best found path
        return self.path_table["AS_PATH"][best_path_index].split()[0]

    def find_best_path(self, possible_path_indexes):
        """
        Preferences:
        1. the path with the highest WEIGHT
        2. the path with the highest LOC_PREF
        3. the path with the lowest TRUST_RATE
        4. the path with the shortest AS_PATH
        5. the path with the lowest MED
        """
        # compare the entries
        res = []
        for i in possible_path_indexes:
            if not res:
                res = i

            if self.path_table["WEIGHT"][res] < self.path_table["WEIGHT"][i]:
                res = i
                continue

            if self.path_table["LOC_PREF"][res] < self.path_table["LOC_PREF"][i]:
                res = i
                continue

            if self.path_table["TRUST_RATE"][res] > self.path_table["TRUST_RATE"][i]:
                res = i
                continue

            if len(self.path_table["AS_PATH"][res]) > len(
                self.path_table["AS_PATH"][i]
            ):
                res = i
                continue

            if self.path_table["MED"][res] > self.path_table["MED"][i]:
                res = i
                continue

        return res

    def check_if_local_delivery(self, ip_packet):
        # Check the destination address, if it matches, you're done
        if self.ip == ip_packet.get_destination_addr():
            return True

        for addr in self.advetised_prefixes:
            if ipaddress.IPv4Address(
                ip_packet.get_destination_addr()
            ) in ipaddress.ip_network(addr):
                s_print(
                    f"Packet for one of our announced prefixes at router {self.name}!"
                )
                return True

        return False

    def add_advertised_ip_prefix(self, advertised_ip):
        for ip in advertised_ip:
            self.advetised_prefixes.add(ip)

    def advertise_ip_prefix(self, path_attr, ip_prefix):
        """
        Advertise the passed prefix.
        """
        for r in self.paths:
            # send the UPDATE message
            self.bgp_send(
                r,
                UpdateMessage(
                    self.name,
                    total_pa_len=len(path_attr.keys()),
                    total_pa=path_attr,
                    nlri=ip_prefix,
                ),
            )

    def start_voting(self, peer_list):
        logger.debug(f"Router {self.name} wants to get votes for {peer_list}")
        for peer in peer_list:
            logger.debug(
                f"Router {self.name} requesting voting messages for peer {peer}"
            )
            self.bgp_send(peer, VotingMessage(self.name, self.name, 0, peer))

    def bgp_send(self, peer_to_send, data):
        l_bgp_port = 2000 + 4 * int(peer_to_send)
        self.speaker.bgp_send_message(l_bgp_port, data)

    def data_send(self, peer_to_send, data):
        l_data_port = 2000 + 4 * int(peer_to_send) + 2
        self.speaker.send_data(l_data_port, data)

    def handle_data(self, ip_packet):
        logger.debug(f"Router {self.name} received an IP packet!")
        # validate the packet
        if not ip_packet.validate():
            logger.debug(f"IP packet not valid at router {self.name}!")
            return

        # check if the packet is for us
        if self.check_if_local_delivery(ip_packet):
            s_print(f"IP packet found its home at AS {self.name}")
            s_print(
                f"Packet destination addr: {ip_packet.get_destination_addr()}\nContents:\n\t{ip_packet.get_payload()}"
            )
            return

        # at this point, find the next hop
        next_hop_peer = self.determine_next_hop(ip_packet)
        if not ip_packet.decrease_ttl():
            logger.debug(f"Router {self.name} dropping an IP packet")
            return

        ip_packet.generate_new_checksum()

        self.message_scheduler.enter(0.2, 1, self.data_send, (next_hop_peer, ip_packet))
        self.message_scheduler.run()

    def handle_bgp_data(self, bgp_message):
        """
        Handles and qualifies the received message from a BGP speaker.
        """
        try:
            peer = int(bgp_message.get_sender())
            self.messages_exchanged[peer] += 1
        except (ValueError, KeyError):
            logger.debug(
                f"In router {self.name}: {self.messages_exchanged}, peer: {peer}"
            )
            logger.debug(f"message type: {bgp_message.get_message_type()}")
            raise FiniteStateMachineError()

        if bgp_message.get_message_type() == Message.MESSAGE:
            # general BGP messages will be used to just notify the listeners that a TCP
            # connection has been set up
            if isinstance(self.sm.get_state(peer), states.IdleState):
                self.sm.switch_state(
                    peer, Event("ManualStart")
                )  # is now in Connect state
                self.sm.switch_state(
                    peer, Event("TcpConnectionConfirmed")
                )  # is now in Active state

                # generate the initial random trust value for our peer
                self.trust_values[peer] = get_random_trust_value()

                # schedule the speaker to send an open message to the peer
                self.message_scheduler.enter(
                    0.2, 1, self.bgp_send, (peer, OpenMessage(self.name, self.ip))
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.OPEN:
            if isinstance(self.sm.get_state(peer), states.ActiveState):
                self.message_scheduler.enter(
                    0.2, 1, self.bgp_send, (peer, OpenMessage(self.name, self.ip))
                )
                self.message_scheduler.run()
                self.sm.switch_state(
                    peer, Event("TcpConnectionConfirmed")
                )  # is now in OpenSent state
                return

            if isinstance(self.sm.get_state(peer), states.OpenSentState):
                self.sm.switch_state(
                    peer, Event("BGPOpen")
                )  # is now in OpenConfirm state
                bgp_message.verify()
                self.message_scheduler.enter(
                    0.2, 1, self.bgp_send, (peer, KeepAliveMessage(self.name))
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.UPDATE:
            logger.debug(f"Router {self.name} received an UPDATE message from {peer}")
            if isinstance(self.sm.get_state(peer), states.EstablishedState):
                # we got an update message, time to update routing table
                propagate = self.update_routing_table(bgp_message)

                if not propagate:
                    self.updates_received += 1
                    if self.updates_received >= len(self.paths):
                        self.advertise_setup_complete = True
                    return

                # construct new update values
                new_path_attr = bgp_message.get_path_attr()
                new_path_attr["NEXT_HOP"] = self.ip
                # the entry we just completed is the last one
                new_path_attr["TRUST_RATE"] = self.path_table["TRUST_RATE"][-1]
                new_path_attr["AS_PATH"] = f"{self.name} " + new_path_attr["AS_PATH"]
                # send new update message
                self.message_scheduler.enter(
                    0,
                    1,
                    self.advertise_ip_prefix,
                    (new_path_attr, bgp_message.get_nlri()),
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.NOTIFICATION:
            logger.debug("Notification message received. Going back to idle state...")
            self.trust_values[peer] -= 0.1

        if bgp_message.get_message_type() == Message.KEEPALIVE:
            if isinstance(self.sm.get_state(peer), states.OpenConfirmState):
                self.sm.switch_state(
                    peer, Event("KeepAliveMsg")
                )  # is now in Established state
                logger.debug(
                    f"Router {self.name} is now in state {self.sm.get_state(peer)}"
                    f" with peer {peer}"
                )
                self.message_scheduler.enter(
                    10, 1, self.bgp_send, (peer, KeepAliveMessage(self.name))
                )
                self.message_scheduler.run()
                return

            if isinstance(self.sm.get_state(peer), states.EstablishedState):
                self.bgp_setup_complete = True

                self.message_scheduler.enter(
                    15, 1, self.bgp_send, (peer, KeepAliveMessage(self.name))
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.VOTING:
            # verify message and decrease TTL value
            bgp_message.verify()

            # case 1: the message is to be forwarded to the 2nd neighbours
            if not bgp_message.is_at_2nd_point() and not bgp_message.is_answer():
                second_neighbours = list(self.paths)
                second_neighbours.remove(int(bgp_message.get_origin()))
                logger.debug(
                    f"Forwarding VOTING message from {bgp_message.get_origin()} for "
                    f"router to {self.name} to 2nd neighbours: {second_neighbours}"
                )
                bgp_message.set_router_num(self.name)
                bgp_message.set_num_of_2nd_neighbours(len(second_neighbours))
                if not second_neighbours:
                    bgp_message.set_to_answer()
                    self.message_scheduler.enter(0.2, 1, self.bgp_send, (bgp_message.get_origin(), bgp_message))
                    self.message_scheduler.run()

                for p in second_neighbours:
                    self.message_scheduler.enter(0.2, 1, self.bgp_send, (p, bgp_message))
                    self.message_scheduler.run()
                return

            # case 2: the message is at a 2nd neighbour
            if bgp_message.is_at_2nd_point() and not bgp_message.is_answer():
                # get own trust value
                vote_value = self.trust_values[peer]

                logger.debug(
                    f"VOTING for {bgp_message.get_peer_to_vote_for()} by request of "
                    f"router {bgp_message.get_origin()} with value {vote_value}."
                )
                # create new VOTING message and send it back to the peer in question
                new_vote_msg = VotingMessage(
                    self.name,
                    bgp_message.get_origin(),
                    1,
                    bgp_message.get_peer_to_vote_for(),
                    vote_value,
                )
                new_vote_msg.set_num_of_2nd_neighbours(
                    bgp_message.get_num_of_2nd_neighbours()
                )
                self.message_scheduler.enter(
                    0.2,
                    1,
                    self.bgp_send,
                    (
                        bgp_message.get_peer_to_vote_for(),
                        new_vote_msg,
                    ),
                )
                self.message_scheduler.run()
                return

            # case 3: the message is to be forwarded back to origin
            if not bgp_message.is_at_2nd_point() and bgp_message.is_answer():
                logger.debug(
                    f"Forwarding VOTING message back to origin {bgp_message.get_origin()}"
                    f" from router {self.name}"
                )
                bgp_message.set_router_num(self.name)
                self.message_scheduler.enter(
                    0.2, 1, self.bgp_send, (bgp_message.get_origin(), bgp_message)
                )
                self.message_scheduler.run()
                return

            # case 4: the message is back to the original sender
            if bgp_message.is_at_2nd_point() and bgp_message.is_answer():
                logger.debug(
                    f"Received VOTING message from {peer} at router {self.name}"
                )
                if not bgp_message.get_num_of_2nd_neighbours():
                    self.update_voting_value(
                        bgp_message.get_peer_to_vote_for(),
                        bgp_message.get_num_of_2nd_neighbours()
                    )
                    return

                self.update_voting_value(
                    bgp_message.get_peer_to_vote_for(),
                    bgp_message.get_num_of_2nd_neighbours(),
                    bgp_message.get_vote_value(),
                )
                return

        if bgp_message.get_message_type() == Message.TRUSTRATE:
            if self.messages_exchanged[peer] > 20:
                self.trust_values[peer] += 0.1

            self.messages_exchanged[peer] -= 20
            self.message_scheduler.enter(
                15, 1, self.bgp_send, (peer, TrustRateMessage(self.name))
            )
            self.message_scheduler.run()
            return

            # check if we are already contained in the AS path
            # if self.name in bgp_message.get_as_path().split():
            #     # do nothing and return
            #     return
            #
            # # received the trust message, which means we need to update our table
            # try:
            #     # add our own trust value of the peer to the received value
            #     peer_trust = self.path_table["TRUST_RATE"][
            #         self.path_table["AS_PATH"].index(str(peer))
            #     ]
            #     index = self.path_table["AS_PATH"].index(bgp_message.get_as_path())
            #     new_as_pah = str(self.name) + " " + bgp_message.get_as_path()
            #     logger.debug(
            #         f"Adding new TRUST value in router {self.name} with AS_PATH of {bgp_message.get_as_path()}"
            #         f"and value of {peer_trust + bgp_message.get_trust_value()}"
            #     )
            #     new_trust_value = peer_trust + bgp_message.get_trust_value()
            #     self.customise_routing_table(index, "t", new_trust_value)
            # except ValueError as e:
            #     logger.error(f"ERROR: {e}")
            #     return
            #
            # # pass along the trust message for any AS num that is not in the AS path
            # # of the trust message
            # for p in self.paths:
            #     if p not in bgp_message.get_as_path().split():
            #         self.message_scheduler.enter(
            #             1,
            #             1,
            #             self.bgp_send,
            #             (p, TrustRateMessage(self.name, new_trust_value, new_as_pah)),
            #         )
            #         self.message_scheduler.run()
            # return

        self.sm.switch_state(peer, Event("ManualStop"))
        logger.error("Something went wrong. Going back to Idle state!")


class RouterListener:
    def __init__(self, name, bgp_port, data_port):
        self.name = name
        self.bgp_port = bgp_port
        self.data_port = data_port

        # Control and Data plane listener
        self.listen_bgp_socket = socket.create_server((socket.gethostname(), bgp_port))
        self.listen_data_socket = socket.create_server(
            (socket.gethostname(), data_port)
        )


class RouterSpeaker:
    def __init__(self, name, bgp_port, data_port):
        self.name = name
        self.bgp_port = bgp_port
        self.data_port = data_port

        # BGP control and data plane speaker
        self.speaker_bgp_socket = None
        self.speaker_data_socket = None

    def _bgp_connect(self, listener_port):
        self.speaker_bgp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_bgp_socket.connect((socket.gethostname(), listener_port))

    def bgp_send_message(self, l_port, data):
        self._bgp_connect(l_port)
        s = self.speaker_bgp_socket.send(
            pickle.dumps(data),
        )
        self.speaker_bgp_socket.close()

    def _data_connect(self, listener_port):
        self.speaker_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_data_socket.connect((socket.gethostname(), listener_port))

    def send_data(self, l_port, data):
        self._data_connect(l_port)
        s = self.speaker_data_socket.send(
            pickle.dumps(data),
        )
        self.speaker_data_socket.close()
