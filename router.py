import socket
from threading import Thread
import time

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
    def __init__(self, name, ip, discovered_paths):
        self.name = name
        self.ip = ip
        # self.sm = BGPStateMachine()
        self.paths = discovered_paths
        self.path_table = {}

        # BGP receiving and listening sockets
        self.speaker = RouterSpeaker()
        self.listener = RouterListener()

    def generate_routing_table(self, paths):
        if not self.path_table:




class RouterListener:
    def __init__(self, port=None):
        self.port = port
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((socket.gethostname(), port))

    def listen(self, connections=11):
        self.listen_socket.listen(connections)

    def accept(self):
        while True:
            client_socket, client_addr = self.listen_socket.accept()
            print("received connection from: " + str(client_addr) + "\r\n")
            client_socket.send("connection accepted".encode("ascii"))
            client_socket.close()


class RouterSpeaker:
    def __init__(self, port=None):
        self.port = port
        self.speaker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, server_port):
        self.speaker_socket.connect((socket.gethostname(), server_port))
        incoming_msg = self.speaker_socket.recv(1024)

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
