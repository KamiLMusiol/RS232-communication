import serial
import serial.tools.list_ports
from enums import Parity, FlowControl, Terminator


class SerialInterface:





    def __init__(self):
        self.connection = serial.Serial() #uchwyt do obsugi rs232
        self.port_name = self.auto_select_rs232_prolific()
        self.active_terminator = ""
        self.connection.timeout = 2  # jak po 2 sekundach nic sie nie stanie to program sie nie zawiesi



    def close(self):
        """Zamyka połączenie z portem zwalnia go"""
        if self.connection.is_open:
            self.connection.close()
            print("Port został zamknięty.")
    #zadanie 1.1 Wybór portu (połączony ze sprawdzeniem obecności portu)

    #funckja sprawdzająca używane porty - extra
    def list_and_check_ports(self):
        print(f"\n\n{'-' * 10}Sprawdzanie dostepnosci portow....{'-' * 10}\n")
        #lista podpietych portów
        dostepne_porty = list(serial.tools.list_ports.comports())

        if not dostepne_porty:
            print("no ports")

        print(f"Lista portow:")
        for i,ports in enumerate(dostepne_porty):
             print(f"{i}: {ports.device} - {ports.description}")


        print(f"\n\n{'-' * 10} True rs232{'-' * 10}")
        for i,ports in enumerate(dostepne_porty):
            if ports.vid == 0x067B: #numer vid naszego kabla ugreen to 1659 - 0x067B kabel prolific
                print(f"Układ USB-RS232: {ports.device} - {ports.description}", end="")


    #funkcja która zwraca NAZWE portu na ktorym jest rs232
    def auto_select_rs232_prolific(self):

        print(f"\n\n{'-' * 10}Próba znaleznienia urzadzenia ugreen....{'-' * 10}")
        dostepne_porty = list(serial.tools.list_ports.comports())

        for p in dostepne_porty:
            if p.vid == 0x067B: #numer vid naszego kabla ugreen to 1659 - 0x067B kabel prolific
                print(f" Znaleziono rs232 od prolific ugreen na porcie {p}  ")

                try:
                    self.connection.port = p.device
                    self.connection.open()
                    print(f"\n {'-' * 10}Próba podłączenia....{'-' * 10}")
                    if self.connection.is_open:
                        print(f"Port {p.device} z r232 poprawnie podlaczony ")
                        #self.connection.close()
                        return p.device # zwracamy nazwę  portu

                except Exception as e:
                        print(f"Znaleziono {p.device}, ale nie mozna podlaczyc: {e}")

        print(" Nie znaleziono żadnego adaptera Prolific!")
        return None



    #zadanie 1.2 Ustawienie parametrów transmisyjnych  szybkość (od 150 bit/s do 115 kb/s) format znaku (7 lub 8 bitowe pole danych, kontrola: E, O lub N, 1 lub 2 bity stop)
    #zadanie 1.3. Kontrola przepływu - OB brak kontroli przepływu,„sprzętowa” (handshake): DTR/DSR, RTS/CTS, “programowa”: XON/XOFF #
    def configure_rs232(self, baudrate: int = 9600, bytesize: int = 8, parity: Parity = Parity.NONE, stopbits: int = 1, flow: FlowControl = FlowControl.NONE):
        """
        Konfiguruje parametry portu przenosi ustawienia do sterownika
        :param baudrate(int): Szybkość transmisji (np. 9600, 115200)
        :param bytesize(int): Liczba bitów danych w ramce (7 lub 8)
        :param parity(Parity): Typ parzystości: 'N' (None), 'E' (Even), 'O' (Odd).
        :param stopbits(int): Liczba bitów stopu (1 lub 2)


        """
        try:
            self.connection.baudrate = baudrate
            self.connection.bytesize = bytesize
            self.connection.parity = parity.value
            self.connection.stopbits = stopbits

            # Logika Flow Control (1.3)
            self.connection.xonxoff = (flow == FlowControl.XONXOFF)
            self.connection.rtscts = (flow == FlowControl.RTSCTS)
            self.connection.dsrdtr = (flow == FlowControl.DSRDTR)

            print(f"Udało się! Skonfigurowano: {baudrate}bps, {bytesize}{parity.name}{stopbits}, Flow: {flow.name}")
        except Exception as e:
            print(f" Konfiguracja nieudana: {e}")

    # zadanie 1.4 Przepływ sterowany „ręcznie”: – możliwość ustawienia „na życzenie” wyjść DTR lub RTS, monitoring stanu wejść DSR, CTS - OP

    #czesc pozwalajaca mowic do drugiego uradzenia
    def set_manual_lines(self, rts: bool = False, dtr: bool = False):
        """Ustawia stany linii wyjściowych na życzenie.
        rts (Request to Send – Żądanie wysłania) Fizycznie: Pin nr 7 we wtyczce DB9. używany do sprzętowego przepływu danych (Handshaking) "mozesz do mnie wysylac"
        dtr (Data Terminal Ready – Gotowość terminala) Fizycznie: Pin nr 4 we wtyczce DB9 Informuje drugie urządzenie, że Twój program jest uruchomiony i port jest aktywny („Mój program jest uruchomiony, port jest otwarty i jestem gotowy do pracy”).
        Działanie:
        rts = True, dtr = True -normalna rozmowa wysylanie i odbieranie
        rts = True - chce przyjmowac dane
        dtr = True - chce wysylac dane, mam taka chec po drugiej stroinie rts musi byc = True
        default - brak rozmowy

        """
        if self.connection.is_open:
            if rts is not None: self.connection.rts = rts
            if dtr is not None: self.connection.dtr = dtr
            print(f"[1.4] Linie ustawione -> RTS: {rts}, DTR: {dtr}")




    def get_input_monitoring(self):
        """Monitoruje stan wejść DSR i CTS.
        CTS (Clear to Send – Gotów do odbioru), Pin nr 8 we wtyczce DB9. odpowiedź na  sygnał RTS - tu to wchodzi. Jeśli druga strona dostanie na CTS = True, pozwala na wysylanie danych do komputera wysyłającego sygnal rts . Sąsiad ma wolny bufor mozna do niego wyslac dane
        DSR (Data Set Ready) -upewnia sie z urzadzenie po drugiej stornie jest gotowe odpowiada na dtr jest wejsciem jezeli true urzadzenie pod drugiej stroanie jest wlaczone gotowe do rozmowy
        dsr - true pozwala na odbieranie danych
        cts - pozwolenie na wysylanie danych
        """
        if self.connection.is_open:
            return {
                "CTS": self.connection.cts,
                "DSR": self.connection.dsr
            }

    # Zadanie 1.5: Wybór terminatora (OB) - tego co rbi nowa linjke
    def set_terminator(self, term: Terminator, custom: str = ""):
        """Ustawia terminator standardowy lub własny (do 2 znaków).\



        """
        if term == Terminator.CUSTOM:
            self.active_terminator = custom[:2] #tylko 01 nie dalej jezeli nic nie bedzei zadziala jak NONE
        else:
            self.active_terminator = term.value
        print(f"[1.5] Terminator ustawiony na: {repr(self.active_terminator)}")

    #zadanie 2
    # Nadawanie - OB
    def send_message(self, text: str):

        if self.connection.is_open:
            # 1. Doklejamy wybrany w 1.5 terminator
            full_message = text + self.active_terminator

            # 2. Zamieniamy tekst na bajty (UTF-8) i wysyłamy
            self.connection.write(full_message.encode('utf-8'))
            print(f"[2.1] Wysłano: {repr(full_message)}")

    #zadanie 3
    # Odbiór - OB
    def receive_message(self):
        """Zadanie 2.2: Odbiera dane aż do napotkania terminatora."""
        if self.connection.is_open:
            # Czekamy na dane, aż pojawi się nasz terminator
            # timeout w __init__ zapobiegnie zawieszeniu programu
            raw_data = self.connection.read_until(self.active_terminator.encode('utf-8'))


            if raw_data:
                decoded_msg = raw_data.decode('utf-8')
                print(f"[2.2] Odebrano: {repr(decoded_msg)}")
                return decoded_msg
        return None
