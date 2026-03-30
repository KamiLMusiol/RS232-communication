import serial
import serial.tools.list_ports



class SerialInterface:
    def __init__(self):
        self.connection = None

    #zadanie 1.1 Wybór portu (połączony ze sprawdzeniem obecności portu)

    def list_and_check_ports(self):

        #lista podpietych portów
        dostepne_porty = list(serial.tools.list_ports.comports())

        if not dostepne_porty:
            print("no ports")

        print(f"\n\n{'-' *10} Listed ports {'-' *10}")
        for i,ports in enumerate(dostepne_porty):
             print(f"{i}: {ports.device} - {ports.description}")


        print(f"\n\n{'-' * 10} True rs232{'-' * 10}")
        for i,ports in enumerate(dostepne_porty):
            if ports.vid == 0x067B: #numer vid naszego kabla ugreen to 1659 - 0x067B kabel prolific
                print(f"Układ USB-RS232: {ports.device} - {ports.description}", end="")






