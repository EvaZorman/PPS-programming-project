import ipaddress
import logging
import pickle
import random
import sched
import select
import socket
import threading

import pandas

import states
from events import Event
from messages import (
    UpdateMessage,
    KeepAliveMessage,
    OpenMessage,
    NotificationMessage,
    FiniteStateMachineError,
    Message,
    VotingMessage,
    BGPMessage,
    TrustRateMessage,
)
from state_machine import BGPStateMachine

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

BUFFER_SIZE = 1024  # Normally 1024

S_PRINT_LOCK = threading.Lock()


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

        self.setup_complete = False
        self.sm = BGPStateMachine(f"SM-{name}", 5, discovered_paths)
        self.message_scheduler = sched.scheduler()

        self.paths = discovered_paths
        self.vote_rates = {peer: [] for peer in discovered_paths}

        self.path_table = {
            "NETWORK": [],
            "NEXT_HOP": [],
            "MED": [],
            "LOC_PREF": [],
            "WEIGHT": [],
            "TRUST_RATE": [],
            "AS_PATH": [],
        }

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
                    # check where to pass it to
                    s_print("received connection from: " + str(data_client_addr))
                    data_client_socket.send("connection accepted".encode("ascii"))
                    data_client_socket.close()

    def stop(self):
        self.stop_listening.set()

    def update_voting_value(self, peer, num_of_2nd_neighbours, voted_trust_value):
        self.vote_rates[peer].append(voted_trust_value)

        # if we have all the votes from the 2nd neighbours, update the new
        # trust value
        if len(self.vote_rates[peer]) == num_of_2nd_neighbours:
            # get index value of the peer
            index = self.path_table["AS_PATH"].index(str(peer))
            s_print(f"Got index for peer {peer} at: {index}")

            voted_trust = 0
            for v in self.vote_rates[peer]:
                voted_trust += v
            voted_trust = voted_trust / len(self.vote_rates[peer])

            # construt the new trust value
            self.path_table["TRUST_RATE"][index] = 1 / (
                0.4 * self.path_table["TRUST_RATE"][index]
            ) + (0.6 * (voted_trust / len(self.vote_rates[peer])))

            self.vote_rates[peer].append(voted_trust_value)
            s_print(f"New voting table: {self.vote_rates}")

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

    def get_routing_table_size(self):
        return len(self.path_table["MED"])

    def update_routing_table(self, data):
        pa = data.get_path_attr()
        nlri = data.get_nlri()

        for i in nlri:
            if self.name in pa["AS_PATH"]:
                return False

            if "TRUST_RATE" not in pa:
                self.path_table["TRUST_RATE"].append(get_random_trust_value())
            else:
                self.path_table["TRUST_RATE"].append(pa["TRUST_RATE"])

            self.path_table["NETWORK"].append(i)
            self.path_table["NEXT_HOP"].append(pa["NEXT_HOP"])
            self.path_table["MED"].append(pa["MED"])
            self.path_table["LOC_PREF"].append(pa["LOCAL_PREF"])
            self.path_table["WEIGHT"].append(pa["WEIGHT"])
            self.path_table["AS_PATH"].append(pa["AS_PATH"])

        return True

    def customise_routing_table(self, row, choice, value):
        if choice == "m":
            self.path_table["MED"][row] = value
        if choice == "l":
            self.path_table["LOC_PREF"][row] = value
        if choice == "w":
            self.path_table["WEIGHT"][row] = value
        if choice == "t":
            self.path_table["TRUST_RATE"][row] = value
        self.print_routing_table()

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
        Preferences:
        1. the path with the highest WEIGHT
        2. the path with the highest LOCAL_PREF
        3. the path with the lowest TRUST_RATE
        4. the path with the shortest AS_PATH
        5. the path with the lowest MED
        """
        # get all stored networks
        netw_addresses = set(self.path_table["NETWORK"])
        # get the longest address match for the ip packet destination
        common_bits_list = []
        for addr in netw_addresses:
            common_bits_list.append(
                int(ipaddress.IPv4Address(ip_packet.get_destination_addr()))
                ^ int(ipaddress.ip_network(addr).network_address)
            )
        # as far as i can see, we can really only XOR easily in Python, so let's
        # XOR the addresses and the smallest value is the best match
        print(common_bits_list)
        longest_addr_match = common_bits_list[common_bits_list.index(min(common_bits_list))]

        # find all entries that lead to that destination
        possible_paths = [x for x in self.path_table["AS_PATH"] if ]
        # run the checks to find the best path

        pass

    def check_if_local_delivery(self, ip_packet):
        # Check the destination address, if it matches, you're done
        if self.ip == ip_packet.get_destination_addr():
            return True
        return False

    def advertise_ip_prefix(self, path_attr, ip_prefix):
        """
        Advertise the passed prefix.
        """
        self.setup_complete = False

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
        s_print(f"Router {self.name} wants to get votes for {peer_list}")
        for peer in peer_list:
            s_print(f"Router {self.name} requesting voting messages for peer {peer}")
            self.bgp_send(peer, VotingMessage(self.name, self.name, 0, peer))

    def bgp_send(self, peer_to_send, data):
        l_bgp_port = 2000 + 4 * int(peer_to_send)
        self.speaker.bgp_send_message(l_bgp_port, data)

    def handle_bgp_data(self, bgp_message):
        """
        Handles and qualifies the received message from a BGP speaker.
        """
        try:
            peer = int(bgp_message.get_sender())
        except ValueError:
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
                # schedule the speaker to send an open message to the peer
                self.message_scheduler.enter(
                    1, 1, self.bgp_send, (peer, OpenMessage(self.name, self.ip))
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.OPEN:
            if isinstance(self.sm.get_state(peer), states.ActiveState):
                self.message_scheduler.enter(
                    1, 1, self.bgp_send, (peer, OpenMessage(self.name, self.ip))
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
                    1, 1, self.bgp_send, (peer, KeepAliveMessage(self.name))
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.UPDATE:
            print(f"Router {self.name} received an UPDATE message from {peer}")
            if isinstance(self.sm.get_state(peer), states.EstablishedState):
                # we got an update message, time to update table
                propagate = self.update_routing_table(bgp_message)

                if not propagate:
                    return

                # construct new update values
                new_path_attr = bgp_message.get_path_attr()
                new_path_attr["NEXT_HOP"] = self.ip
                new_path_attr["TRUST_RATE"] = 0
                new_path_attr["AS_PATH"] = f"{self.name} " + new_path_attr["AS_PATH"]
                # send new update message
                self.message_scheduler.enter(
                    1,
                    1,
                    self.advertise_ip_prefix,
                    (new_path_attr, bgp_message.get_nlri()),
                )
                self.message_scheduler.run()
                return

        if bgp_message.get_message_type() == Message.NOTIFICATION:
            s_print("Notification message received. Going back to idle state...")
            # reduce trust rate of peer

        if bgp_message.get_message_type() == Message.KEEPALIVE:
            if isinstance(self.sm.get_state(peer), states.OpenConfirmState):
                self.sm.switch_state(
                    peer, Event("KeepAliveMsg")
                )  # is now in Established state
                s_print(
                    f"Router {self.name} is now in state {self.sm.get_state(peer)}"
                    f"with peer {peer}"
                )

                # check if all connections are set up
                if self.sm.all_setup():
                    self.setup_complete = True
                return

        if bgp_message.get_message_type() == Message.VOTING:
            # verify message and decrease TTL value
            bgp_message.verify()

            # case 1: the message is to be forwarded to the 2nd neighbours
            if not bgp_message.is_at_2nd_point() and not bgp_message.is_answer():
                second_neighbours = list(self.paths)
                second_neighbours.remove(int(bgp_message.get_origin()))
                s_print(
                    f"Forwarding VOTING message from {bgp_message.get_origin()} for "
                    f"router to {self.name} to 2nd neighbours: {second_neighbours}"
                )
                bgp_message.set_num_of_2nd_neighbours(len(second_neighbours))
                for p in second_neighbours:
                    self.message_scheduler.enter(1, 1, self.bgp_send, (p, bgp_message))
                    self.message_scheduler.run()
                return

            # case 2: the message is at a 2nd neighbour
            if bgp_message.is_at_2nd_point() and not bgp_message.is_answer():
                # get own trust value
                index = self.path_table["AS_PATH"].index(
                    str(bgp_message.get_peer_to_vote_for())
                )
                vote_value = self.path_table["TRUST_RATE"][index]

                s_print(
                    f"VOTING for {bgp_message.get_peer_to_vote_for()} by request of "
                    f"router {bgp_message.get_origin()} with value {vote_value}."
                )
                # create new VOTING message and send it back to the peer in question
                vote_msg = VotingMessage(
                    self.name,
                    bgp_message.get_origin(),
                    1,
                    bgp_message.get_peer_to_vote_for(),
                    vote_value,
                )
                vote_msg.set_num_of_2nd_neighbours(
                    bgp_message.get_num_of_2nd_neighbours()
                )
                self.message_scheduler.enter(
                    1,
                    1,
                    self.bgp_send,
                    (
                        bgp_message.get_peer_to_vote_for(),
                        vote_msg,
                    ),
                )
                self.message_scheduler.run()
                return

            # case 3: the message is to be forwarded back to origin
            if not bgp_message.is_at_2nd_point() and bgp_message.is_answer():
                s_print(
                    f"Forwarding VOTING message back to origin {bgp_message.get_origin()}"
                    f" from router {self.name}"
                )
                self.message_scheduler.enter(
                    1, 1, self.bgp_send, (bgp_message.get_origin(), bgp_message)
                )
                self.message_scheduler.run()
                return

            # case 4: the message is back to the original sender
            if bgp_message.is_at_2nd_point() and bgp_message.is_answer():
                s_print(f"Received VOTING message from {peer} at router {self.name}")
                self.update_voting_value(
                    bgp_message.get_peer_to_vote_for(),
                    bgp_message.get_num_of_2nd_neighbours(),
                    bgp_message.get_vote_value(),
                )
                return

        if bgp_message.get_message_type() == Message.TRUSTRATE:
            # check if we are already contained in the AS path
            if self.name in bgp_message.get_as_path().split():
                print("BIG NONO, we dropping this like a hot potato!")
                return

            # received the trust message, which means we need to update our table
            try:
                # add our own trust value of the peer to the received value
                peer_trust = self.path_table["TRUST_RATE"][
                    self.path_table["AS_PATH"].index(str(peer))
                ]
                index = self.path_table["AS_PATH"].index(bgp_message.get_as_path())
                new_as_pah = str(self.name) + " " + bgp_message.get_as_path()
                print(
                    f"Adding new TRUST value in router {self.name} with AS_PATH of {bgp_message.get_as_path()}"
                    f"and value of {peer_trust + bgp_message.get_trust_value()}"
                )
                new_trust_value = peer_trust + bgp_message.get_trust_value()
                self.customise_routing_table(index, "t", new_trust_value)
            except ValueError as e:
                print(f"EVEN BIGGER ERROR IN router {self.name} YO!")
                return

            # pass along the trust message for any AS num that is not in the AS path
            # of the trust message
            for p in self.paths:
                if p not in bgp_message.get_as_path().split():
                    self.message_scheduler.enter(
                        1,
                        1,
                        self.bgp_send,
                        (p, TrustRateMessage(self.name, new_trust_value, new_as_pah)),
                    )
                    self.message_scheduler.run()
            return

        # reduce trust rate of peer
        # s_print(f"Got message from {peer} and it's a bad bad message!")
        # self.trust_rates[peer]["TRUST_RATE"] -= 0.05
        self.sm.switch_state(peer, Event("ManualStop"))
        s_print("Something went wrong. Going back to Idle state!")


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
        # TODO check if all data was sent
        s = self.speaker_bgp_socket.send(
            pickle.dumps(data),
        )
        self.speaker_bgp_socket.close()

    def _data_connect(self, server_port):
        self.speaker_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_data_socket.connect((socket.gethostname(), server_port))

    def send_data(self, data):
        s = self.speaker_data_socket.send(pickle.dumps(data))
        self.speaker_bgp_socket.close()
