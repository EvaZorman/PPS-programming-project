import socket
import threading
from threading import Thread
import time

import pandas

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
        # self.sm = BGPStateMachine()
        self.paths = discovered_paths # TODO this needs to be actually implemented
        self.path_table = []

        # BGP receiving and listening sockets
        """
        TODO this is ugly... port range will for now always be the router num
        multiplied by 4 (since we need 4 ports), in the range of:
            port: bgp_listener
            port + 1: bgp_speaker
            port + 2: data_listener
            port + 3: data_speaker
        """
        port = 2000 + (4 * router_number)
        self.listener = RouterListener(port, port+2)
        self.speaker = RouterSpeaker(port+1, port+3)

    def listen(self):
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


class RouterListener:
    def __init__(self, bgp_port, data_port):
        print("Created a RouterListener!")
        self.bgp_port = bgp_port
        self.data_port = data_port
        # BGP control plane listener
        self.listen_bgp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_bgp_socket.bind((socket.gethostname(), bgp_port))
        # Data plane listener
        self.listen_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_data_socket.bind((socket.gethostname(), data_port))
        self.stop_listening = threading.Event()

    def listen(self, connections=11):
        self.listen_bgp_socket.listen(connections)
        self.listen_data_socket.listen(connections)

    def accept(self):
        while not self.stop_listening.is_set():
            bgp_client_socket, bgp_client_addr = self.listen_bgp_socket.accept()
            data_client_socket, data_client_addr = self.listen_data_socket.accept()

            if bgp_client_addr:
                print("received connection from: " + str(bgp_client_addr) + "\r\n")
                bgp_client_socket.send("connection accepted".encode("ascii"))
                bgp_client_socket.close()

            if data_client_addr:
                print("received connection from: " + str(data_client_addr) + "\r\n")
                data_client_socket.send("connection accepted".encode("ascii"))
                data_client_socket.close()

    def stop(self):
        self.stop_listening.set()


class RouterSpeaker:
    def __init__(self, bgp_port, data_port):
        print("Created a RouterSpeaker!")
        self.bgp_port = bgp_port
        self.data_port = data_port
        # BGP control plane data speaker
        self.speaker_bgp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_bgp_socket.bind((socket.gethostname(), bgp_port))
        # Data plane speaker
        self.speaker_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.speaker_data_socket.bind((socket.gethostname(), data_port))

    def bgp_connect(self, server_port):
        self.speaker_bgp_socket.connect((socket.gethostname(), server_port))
        incoming_msg = self.speaker_bgp_socket.recv(1024)

        print(incoming_msg.decode("ascii"))

    def send_data(self, server_port):
        self.speaker_data_socket.connect((socket.gethostname(), server_port))
        incoming_msg = self.speaker_data_socket.recv(1024)

        print(incoming_msg.decode("ascii"))


# def router_listener():
#     a1_l = RouterServer(
#         "a1", "IDLE", "10.0.2.15", 444
#     )  # a1_l = a1 listener & a1_s = a1 sender
#     a1_l.listen()
#     a1_l.accept()
#
#
# def router_sender():
#     time.sleep(
#         15
#     )  # Will cause an error if deleted. required time for router to become stable.
#     a1_s = RouterClient("a1", "IDLE", "10.0.2.15", 557)
#     a1_s.connect("10.0.2.6", 444)
#
#
# if __name__ == "__main__":
#     Thread(target=router_listener).start()
#     Thread(target=router_sender).start()
#
# # a3.connect(a1.ip,a1.port)
#
# # a2.listen()
# # a2.accept()
# # this part creates a list of potential useful IPs for simulating 10 different routers
# ip_oct = [i for i in range(2, 14)]
# interfacce_list = []
# for i in ip_oct:
#     interfacce_list.append("127.0.0." + str(i))
