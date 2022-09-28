import socket
from threading import Thread
"""
use class BGP_router to create router objects.

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
class router_server:
    def __init__(self, state, ip, port):
        self.state = state
        self.ip = ip
        self.port = port
        self.routerobject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.routerobject.bind((self.ip, self.port))
        self.clientsocket = 0
        self.clientaddress = '0.0.0.0'  # sample will never be used
        self.incoming_msg = ''

    def listen(self):
        self.routerobject.listen(11)

        print('p1')

    def accept(self):
        while True:
            print('p2')

            self.clientsocket, self.clientaddress = self.routerobject.accept()
            print('received connection from: ', str(self.clientaddress) + '\r\n')
            print('p3')
            self.clientsocket.send('thank you'.encode('ascii'))
            self.clientsocket.close()

#------------------------------------------------------------------
# the following class makes client socket objects

class router_client:

    def __init__(self, state, ip, port):
        print('a')
        self.state = state
        self.ip = ip
        self.port = port
        self.routerobject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.incoming_msg = ''


    def connect(self, server_IP, server_port):
        print('c1')

        self.routerobject.connect((server_IP, server_port))

        self.incoming_msg = self.routerobject.recv(1024)  # GETS STUCK ON THIS LINE
        print('c2')

        print(self.incoming_msg.decode('ascii'))
        print('c3')

def servers():
    a1 = router_server("IDLE", '127.0.0.2', 444)  # for test
    a1.listen()
    a1.accept()

def clients():
    a3 = router_client("IDLE", '127.0.0.3', 557)
    a3.connect('127.0.0.2', 444)

if __name__ == '__main__':
    Thread(target = servers).start()
    Thread(target = clients).start()

# a3.connect(a1.ip,a1.port)

# a2.listen()
# a2.accept()
# this part creates a list of potential useful IPs for simulating 10 different routers
ip_oct = [i for i in range (2,14)]
interfacce_list = []
for i in ip_oct:
    interfacce_list.append('127.0.0.'+str(i))


