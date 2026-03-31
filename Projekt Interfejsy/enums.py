from enum import Enum
import serial


class Parity(Enum):
    """
        Tryby konroli parzystosci
        NONE: Brak bitu parzystości.
        EVEN: Bit parzystości ustawiany tak, by suma jedynek była parzysta.
        ODD: Bit parzystości ustawiany tak, by suma jedynek była nieparzysta.
    """
    NONE = serial.PARITY_NONE
    EVEN = serial.PARITY_EVEN
    ODD = serial.PARITY_ODD

class FlowControl(Enum):
    """
    Mechanizm kontorli przepływów

    XONXOFF: Kontrola programowa (Software). Wykorzystuje znaki ASCII (0x11 i 0x13)
             przesyłane w strumieniu danych do sterowania transmisją.
    RTSCTS: Kontrola sprzętowa (Hardware). Wykorzystuje fizyczne linie sygnałowe
            Request to Send oraz Clear to Send w kablu RS-232.
    DSRDTR: Kontrola sprzętowa (Hardware). Wykorzystuje linie Data Set Ready
            oraz Data Terminal Ready do sygnalizacji gotowości urządzeń.
    """
    NONE = "None"
    XONXOFF = "XON/XOFF"
    RTSCTS = "RTS/CTS"
    DSRDTR = "DTR/DSR"

class Terminator(Enum):
    """
         terminatory wiadomości dla Zadania 1.5.

        znak lub sekwencja znaków dodawana na końcu każdej wysyłanej
        wiadomości, informująca odbiorcę o zakończeniu nadawania ramki tekstu.

        Attributes:
            NONE: Brak znaku kończącego.
            CR: Carriage Return (Powrót karetki, '\\r', ASCII 13). - wraca na początek tej samej linii
            LF: Line Feed (Nowa linia, '\\n', ASCII 10).
            CRLF: Sekwencja '\\r\\n'
            CUSTOM: Flaga sygnalizująca użycie własnego terminatora (1 lub 2 znaki).
        """
    NONE = ""
    CR = "\r"
    LF = "\n"
    CRLF = "\r\n"
    CUSTOM = "CUSTOM"  # Flaga dla własnego znaku