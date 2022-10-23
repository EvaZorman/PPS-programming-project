import pickle
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
    FiniteStateMachineError, BGPMessage,
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
ROUTER_ADDRESSES = {
    # "router name": (bgp_listener, data_listener),
    # ...
}

S_PRINT_LOCK = threading.Lock()


def get_router_addrs(r):
    return ROUTER_ADDRESSES[f"R{r}"]


def get_router(port):
    try:
        for r, p in ROUTER_ADDRESSES.items():
            if port in p:
                return r
    except ValueError:
        return


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
        self.sm = BGPStateMachine(f"SM-{name}", 5, discovered_paths)

        self.paths = discovered_paths
        self.bgp_connections = 0

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
        port = 2000 + (4 * router_number)
        # generate global table of router : port table to enable lookup
        ROUTER_ADDRESSES[f"R{self.name}"] = [port, port+1, port+2, port+3]

        self.listener = RouterListener(f"R{self.name}", port, port + 2)
        self.speaker = RouterSpeaker(f"R{self.name}", port + 1, port + 3)

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
                    print(message)

                    # get the peer who sent this data
                    peer = get_router(message.get_sender())

                    # handle the message based on internal state
                    self.handle_bgp_data(message, peer)
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

    def update_routing_table(self, data):
        # test data
        self.path_table.append(
            ["123.14.15.16", "0.0.0.0", "0", "", "32768", "1", "6 5 6 7"]
        )
        self.print_routing_table()

    def print_routing_table(self):
        s_print(
            pandas.DataFrame(
                self.path_table,
                columns=[
                    "Network",
                    "Next Hop",
                    "Metric",
                    "LocPref",
                    "Weight",
                    "Trust",
                    "Path",
                ],
            )
        )

    def calculate_ip_route(self):
        s_print("calculating...")
        pass

    def broadcast_ip_prefix(self):
        """
        The router has set up all its necessary connections and sends an update
        message which broadcasts its network prefix
        """

    def handle_bgp_data(self, bgp_message, peer):
        """
        Handles and qualifies the received message from a BGP speaker.
        """
        peer = int(peer.replace("R", ""))
        if isinstance(bgp_message, BGPMessage):
            # general BGP messages will be used to just notify the listeners that a TCP
            # connection has been set up
            if isinstance(self.sm.get_state(peer), states.IdleState):
                self.sm.switch_state(peer, Event("ManualStart"))  # is now in Connect state
                self.sm.switch_state(peer, Event("TcpConnectionConfirmed"))  # is now in Active state
                print("in here!")
                return

        if isinstance(bgp_message, OpenMessage):
            if isinstance(self.sm.get_state(peer), states.ActiveState):
                self.sm.switch_state(peer, Event("TcpConnectionConfirmed"))  # is now in OpenSent state
                self.speaker.bgp_send_message(OpenMessage(self.speaker.bgp_port, self.name, self.ip))
                return

            if isinstance(self.sm.get_state(peer), states.OpenSentState):
                self.sm.switch_state(peer, Event("BGPOpen"))  # is now in OpenConfirm state
                bgp_message.verify()
                self.speaker.bgp_send_message(KeepAliveMessage(self.speaker.bgp_port))
                return

        if isinstance(bgp_message, UpdateMessage):
            if isinstance(self.sm.get_state(peer), states.EstablishedState):
                self.update_routing_table(bgp_message)  # we got an update message, time to update table
                return

        if isinstance(bgp_message, NotificationMessage):
            s_print("Notification message received. Going back to idle state...")
            self.sm.switch_state(peer, Event("SomethingWentWrong"))
            return

        if isinstance(bgp_message, KeepAliveMessage):
            if isinstance(self.sm.get_state(peer), states.OpenConfirmState):
                self.sm.switch_state(peer, Event("KeepAliveMsg"))  # is now in Established state
                return

        raise FiniteStateMachineError()

    def initiate_bgp_connection(self, routes):
        for r in routes:
            l_bgp_port, _, _, _ = get_router_addrs(r)
            self.speaker.bgp_connect(l_bgp_port)
            self.speaker.bgp_send_message(
                BGPMessage(self.speaker.bgp_port, self.name)
            )


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

    def bgp_connect(self, listener_port):
        self.speaker_bgp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_bgp_socket.connect((socket.gethostname(), listener_port))

    def bgp_send_message(self, data):
        s = self.speaker_bgp_socket.send(
            pickle.dumps(data),
        )
        self.speaker_bgp_socket.close()

    def data_connect(self, server_port):
        self.speaker_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_data_socket.connect((socket.gethostname(), server_port))

    def send_data(self, data):
        s = self.speaker_data_socket.send(pickle.dumps(data))
        self.speaker_bgp_socket.close()
