import socket
import threading

import pandas

from events import Event
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


# The following class creates a server socket (each port can be used as either server or client.
# no port can be used as both
class Router:
    def __init__(self, name, ip, router_number, discovered_paths):
        self.name = name
        self.ip = ip
        self.sm = BGPStateMachine(f"SM-{name}", 5, discovered_paths)

        self.paths = discovered_paths  # TODO this needs to be actually implemented
        self.path_table = []

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
        self.listener = RouterListener(self.name, port, port + 2)
        self.speaker = RouterSpeaker(self.name, port + 1, port + 3)

    def start(self):
        # switch the sm to Connect state
        self.sm.switch_state(Event("ManualStart"))
        self.listener.listen()
        self.listener.accept()

    def stop(self):
        self.listener.stop()

    def update_routing_table(self, data):
        # test data
        self.path_table.append(
            ["123.14.15.16", "0.0.0.0", "0", "", "32768", "1", "6 5 6 7"]
        )

    def print_routing_table(self):
        print(
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
        print("calculating...")
        pass

    def broadcast_ip_prefix(self):
        """
        The router has set up all its necessary connections and sends an update
        message which broadcasts its network prefix
        """

    def initiate_connections(self, routes):
        for r in routes:
            self.speaker.bgp_connect(
                # TODO waiting on Open Message :D
            )


class RouterListener:
    def __init__(self, name, bgp_port, data_port):
        self.name = name
        self.bgp_port = bgp_port
        self.data_port = data_port
        self.stop_listening = threading.Event()
        # Control and Data plane listener
        self.listen_bgp_socket = socket.create_server((socket.gethostname(), bgp_port))
        self.listen_data_socket = socket.create_server(
            (socket.gethostname(), data_port)
        )

    def listen(self, connections=11):
        self.listen_bgp_socket.listen(connections)
        self.listen_data_socket.listen(connections)

    def accept(self):
        while not self.stop_listening.is_set():
            bgp_client_socket, bgp_client_addr = self.listen_bgp_socket.accept()
            data_client_socket, data_client_addr = self.listen_data_socket.accept()

            if bgp_client_socket:
                # do something based on the data received
                print("received connection from: " + str(bgp_client_addr) + "\r\n")
                bgp_client_socket.send("connection accepted".encode("ascii"))
                bgp_client_socket.close()

            if data_client_socket:
                # check where to pass it to
                print("received connection from: " + str(data_client_addr) + "\r\n")
                data_client_socket.send("connection accepted".encode("ascii"))
                data_client_socket.close()

    def stop(self):
        self.stop_listening.set()


class RouterSpeaker:
    def __init__(self, name, bgp_port, data_port):
        self.name = name
        self.bgp_port = bgp_port
        self.data_port = data_port
        # BGP control plane data speaker
        self.speaker_bgp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.speaker_bgp_socket.bind((socket.gethostname(), bgp_port))
        # Data plane speaker
        self.speaker_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.speaker_data_socket.bind((socket.gethostname(), data_port))

    def bgp_connect(self, listener_port):
        self.speaker_bgp_socket.connect((socket.gethostname(), listener_port))
        self.speaker_bgp_socket.send(
            # TODO once we have an open message, we can send it :D
        )

        incoming_msg = self.speaker_bgp_socket.recv(1024)

        print(incoming_msg.decode("ascii"))

    def send_data(self, server_port):
        self.speaker_data_socket.connect((socket.gethostname(), server_port))
        incoming_msg = self.speaker_data_socket.recv(1024)

        print(incoming_msg.decode("ascii"))
