import socket

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
    def __init__(self,state,ip,port):
        self.state = state
        self.ip = ip
        self.port = port
        self.routerobject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.routerobject.bind((self.ip,self.port))
        self.clientsocket = 0
        self.clientaddress = '0.0.0.0' #sample will never be used
        self.incoming_msg = ''

    def listen(self):
        self.routerobject.listen(11)

    def accept(self):
        while True:
            self.clientsocket, self.clientaddress = self.routerobject.accept()
            print('received connection from: ', str(self.clientaddress) + '\r\n')
            print('s')
            self.clientsocket.send('thank you'.encode('ascii'))
            self.clientsocket.close()

    #def send(self,message):
        #self.routerobject.send(message.encode('ascii'))
    #def close(self):
        #self.routerobject.close()

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
        #self.routerobject.connect(('127.1.1.16', 556))

    def connect(self, server_IP, server_port):
        print('c1')

        #self.routerobject.connect((server_IP,server_port))
        self.incoming_msg = self.routerobject.recv(1024)
        print(self.incoming_msg.decode('ascii'))
        print('c2')
host1 = socket.gethostname()
host2 = socket.gethostname()
host3 = socket.gethostname()

a1 = router_server("IDLE",host1,444) #for test
a2 = router_server("IDLE",host2,556)
a3 = router_client("IDLE",host3,557)
a3.connect(a1.ip,a1.port)
#a3.connect('127.1.1.16','556')
a1.listen()
a1.accept()
a2.listen()
a2.accept()
a3.connect(a1.ip,a1.port)
a3.connect('127.1.1.16','556')
# this part creates a list of potential useful IPs for simulating 10 different routers
ip_oct = [i for i in range (2,14)]
interfacce_list = []
for i in ip_oct:
    interfacce_list.append('127.0.0.'+str(i))


