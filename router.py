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

class BGP_Router:
    def __init__(self,state,ip,port):
        self.state = 'IDLE'
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
        self.clientsocket, self.clientaddress = self.routerobject.accept()
        print('received connection from: ', str(self.clientaddress)+'\r\n')
    def send(self,message):
        self.routerobject.send(message.encode('ascii'))
    def close(self):
        self.routerobject.close()
    def connect(self, server_IP, server_port):
        self.routerobject.connect((server_IP,server_port))
        self.incoming_msg = self.routerobject.recv(2048)
    def changestate(self,state):
        self.state = state
        if self.incoming_msg == 'NOTIFICATION': #to be completed by SAM
            if self.state == "CONNECT":
                self.state = 'ACTIVE'
                """
                to be completed by me, AREF
                """
            else:
                self.state = 'IDLE'
                self.close()
        elif self.incoming_msg == 'UPDATE': #To be completed by SAM
            #update table
            pass
        elif self.incoming_msg == 'KEEPALIVE':
            self.state = "ESTABLISHED"
            #timer =
        else:
            self.state = "OPENSENT" #should be improved later
            #send OPEN msg
            if self.state == 'CONNECT' or self.state == 'ACTIVE':
                self.state = "OPENCONFIRM"
            else:
                self.state = 'ESTABLISHED'




a = BGP_Router("IDLE",'127.1.1.15',5555) #for test

# this part creates a list of potential useful IPs for simulating 10 different routers
ip_oct = [i for i in range (2,14)]
interfacce_list = []
for i in ip_oct:
    interfacce_list.append('127.0.0.'+str(i))


