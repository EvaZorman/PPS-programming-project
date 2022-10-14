class Event:
    def __init__(
        self, name, message=None, reader=None, writer=None, peer_ip=None, peer_port=None
    ):
        self.name = name
        self.message = message
        self.reader = reader
        self.writer = writer
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.serial_num = None

    def get_name(self):
        return self.name

    def get_message(self):
        return self.message

    def get_reader(self):
        return self.reader

    def get_writer(self):
        return self.writer

    def get_peer_ip(self):
        return self.peer_ip

    def get_peer_port(self):
        return self.peer_port

    def get_serial_num(self):
        return self.serial_num

    def set_serial_num(self, serial_num):
        self.serial_num = serial_num
