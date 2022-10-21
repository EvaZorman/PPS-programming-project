class Event:
    def __init__(
        self,
        name,
        message=None,
    ):
        print(f"Created event: {name}")
        self.name = name
        self.message = message
        self.serial_num = None

    def get_name(self):
        return self.name

    def get_message(self):
        return self.message

    def get_serial_num(self):
        return self.serial_num

    def set_serial_num(self, serial_num):
        self.serial_num = serial_num
