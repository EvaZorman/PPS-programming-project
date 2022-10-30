import logging
import pickle
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


class Router:
    def __init__(self, name, ip, router_number, discovered_paths):
        self.name = name
        self.ip = ip

        self.setup_complete = False
        self.sm = BGPStateMachine(f"SM-{name}", 5, discovered_paths)
        self.message_scheduler = sched.scheduler()

        self.paths = discovered_paths
        self.trust_rates = {
            peer: {"trust_rate": 0.5, "messages_exchanged": 0}
            for peer in discovered_paths
        }
        self.vote_rates = {peer: [] for peer in discovered_paths}

        self.path_table = []

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

    def start(self, connections=11):
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

    def update_voting_value(self, peer, voted_trust_value):
        self.vote_rates[peer].append(voted_trust_value)
        s_print(f"New voting table: {self.vote_rates}")

    def get_routing_table_size(self):
        return len(self.path_table)

    def update_routing_table(self, data):
        pa = data.get_path_attr()
        nlri = data.get_nlri()

        for i in nlri:
            if self.name in pa["AS_PATH"]:
                return False

            self.path_table.append(
                [
                    i,
                    pa["NEXT_HOP"],
                    pa["MED"],
                    pa["LOCAL_PREF"],
                    pa["WEIGHT"],
                    0.5,
                    pa["AS_PATH"],
                ]
            )
        return True

    def customise_routing_table(self, row, choice, value):
        new_entry = self.path_table[row]
        if choice == "m":
            new_entry[2] = value
        if choice == "l":
            new_entry[3] = value
        if choice == "w":
            new_entry[4] = value
        if choice == "t":
            new_entry[5] = value
        self.print_routing_table()

    def print_routing_table(self):
        df = pandas.DataFrame(
            self.path_table,
            columns=[
                "Network",
                "Next_Hop",
                "MED",
                "Loc_Pref",
                "Weight",
                "Trust_Rate",
                "AS_Path",
            ],
        )
        s_print(
            f"Routing table for router {self.name}: \n"
            f"{df.sort_values(by='Network').to_string()} \n"
        )

    def calculate_ip_route(self):
        s_print("calculating...")
        pass

    def advertise_ip_prefix(self, path_attr, ip_prefix):
        """
        Advertise the passed prefix.
        """
        self.setup_complete = False

        for r in self.paths:
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
        s_print(f"Sending voting messages to peers!")
        for peer in peer_list:
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
            s_print(
                f"Received VOTING message from {bgp_message.get_origin()}"
                f" for {bgp_message.get_peer_to_vote_for()}"
            )
            is_at_2nd_peer = bgp_message.verify()

            # if we are one of the routers that needs to vote, create a new message
            if is_at_2nd_peer:
                if (
                    bgp_message.get_voting_type()
                    and bgp_message.get_origin() == self.name
                ):
                    # we got our questions answered back
                    s_print(
                        f"Got VOTE for {bgp_message.get_peer_to_vote_for()} with value"
                        f"{bgp_message.get_vote_value()}"
                    )
                    self.update_voting_value(
                        bgp_message.get_peer_to_vote_for(),
                        bgp_message.get_vote_value(),
                    )
                    return

                s_print(
                    f"VOTING for {bgp_message.get_peer_to_vote_for()} with value"
                    f"{self.trust_rates[bgp_message.get_peer_to_vote_for()]}"
                )
                s_print(f"My own trust rates (router {self.name}): {self.trust_rates}")
                self.message_scheduler.enter(
                    1,
                    1,
                    self.bgp_send,
                    (
                        bgp_message.get_peer_to_vote_for(),
                        VotingMessage(
                            self.name,
                            bgp_message.get_origin(),
                            1,
                            bgp_message.get_peer_to_vote_for(),
                            self.trust_rates[bgp_message.get_peer_to_vote_for()][
                                "trust_rate"
                            ],
                        ),
                    ),
                )
                self.message_scheduler.run()
                return

            # if we are forwarding the answers back to the origin
            # 0 = asking for votes, 1 = is an answer
            if bgp_message.get_voting_type():
                s_print(f"Forwarding VOTING message back to origin!")
                self.message_scheduler.enter(
                    1, 1, self.bgp_send, (bgp_message.get_origin(), bgp_message)
                )
                self.message_scheduler.run()
                return

            # we need to forward the vote question to all our neighbours
            # minus the peer we received the question from
            s_print(f"Forwarding VOTING message to 2nd neighbours!")
            peers_to_send = list(self.paths)
            s_print(peers_to_send)
            peers_to_send.remove(peer)
            s_print(peers_to_send)
            for p in peers_to_send:
                self.message_scheduler.enter(1, 1, self.bgp_send, (p, bgp_message))
                self.message_scheduler.run()
            return

        # reduce trust rate of peer
        # s_print(f"Got message from {peer} and it's a bad bad message!")
        # self.trust_rates[peer]["trust_rate"] -= 0.05
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
