import random
import socket
import math
import time
class SocketTCP:
    def __init__(self):
        """
        Create a pedagogical TCP socket

        No-Optional Parameters:
        socket_tcp : create a non-oriented connection socket
        send_to: tuple (IP,Port) of the destination server
        origin: tuple (IP, Port) of the origin client
        buff_size: amount of bytes send by iteration
        seq: seq number 
        """
        self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.success_address = ('localhost', 8555)
        self.send_to = None
        self.origin = None
        self.seq = 0
        self.message_length = None
        self.temp = bytearray()
        self.DEBUG = True
        self.ERROR_DEBUG = True

    def parse_segment(self, segment):
        """
        return (syn:int, ack:int, fin:int, seq:int, data:str)
        """
        elements = segment.split("|||")
        parsed_segment = [
            int(elements[0]),
            int(elements[1]),
            int(elements[2]),
            int(elements[3]),
            elements[4]
        ]
        return parsed_segment

    def create_segment(self, syn, ack, fin, seq, data):
        template = "{SYN}|||{ACK}|||{FIN}|||{SEQ}|||{DATA}"
        return template.format(SYN=syn, ACK=ack, FIN=fin, SEQ=seq, DATA=data)

    def bind(self, address):
        self.origin = address
        self.socket_tcp.bind(address)
    
    def connect(self, address):
        self.socket_tcp.settimeout(5)
        '''     SENDING SECTION     '''
        self.seq = random.randint(0, 100)
        syn_message = self.create_segment(1, 0, 0, self.seq, "")
        ok = False

        while not ok:
            # ---- sending seq ---->
            if self.DEBUG: print(f'-- SENDING SYN, seq = {self.seq} -->', end="\n\n")
            self.socket_tcp.sendto(syn_message.encode(), address)
            try:
                # <---- receiving seq + 1 ----
                
                syn_ack_message, server_adress = self.socket_tcp.recvfrom(48) 
                syn, ack, fin, rec_seq, data = self.parse_segment(syn_ack_message.decode())
                if self.DEBUG: print(f"<-- RECEIVING SYN + ACK, seq = {rec_seq} --", end="\n\n")

                if (syn, ack, fin, rec_seq) == (1, 1, 0, self.seq + 1):
                    if self.DEBUG: print(f"-- SENDING ACK, seq = {self.seq + 1} -->", end="\n\n")
                    self.seq = rec_seq + 1
                    ack_message = self.create_segment(0, 1, 0, self.seq, "")
                    self.socket_tcp.sendto(ack_message.encode(), address)
                    self.send_to = eval(data)
                    ok = True
                    if self.DEBUG: 
                        print("--- ESTABLISHED CONNECTION ---")
                        print(self.send_to)
                    return
            except Exception as e:
                if self.ERROR_DEBUG: print(f"<-- RECEIVING SYN + ACK FAILED, SENDING ACK AGAIN --", end="\n\n")

    def accept(self):
        self.socket_tcp.settimeout(5)
        ok = False
        MAX_ATTEMPS = 5
        curr_attemps = 0
        while not ok:
            try:
                # <---- receiving seq ----
                
                syn_message, self.send_to  = self.socket_tcp.recvfrom(32)
                syn, ack, fin, rec_seq, data = self.parse_segment(syn_message.decode())
                if self.DEBUG: print(f"<-- RECEIVING SYN, seq = {rec_seq} --", end="\n\n")

                self.seq = rec_seq
                new_socket = SocketTCP()
                success = False
                while not success:
                    try:
                        self.success_address = ('localhost', random.randint(8000, 9000))
                        new_socket.bind(self.success_address)
                        success = True
                    except:
                        pass
                syn_ack_message = self.create_segment(1, 1, 0, self.seq + 1, str(self.success_address))
                if (syn, ack, fin, data) == (1, 0, 0, ""):
                    ok = True
            except Exception as e:
                if self.ERROR_DEBUG: print(f"<-- RECEIVING SYN FAILED, TRYING AGAIN --", end="\n\n")

            while ok:
                # ---- sending seq + 1 ---->
                if self.DEBUG: print(f"-- SENDING SYN + ACK, seq = {self.seq + 1} -->", end="\n\n")
                self.socket_tcp.sendto(syn_ack_message.encode(), self.send_to)
                try:
                    # <---- receiving seq + 2 ----  
                    ack_message, self.send_to = self.socket_tcp.recvfrom(32)
                    syn, ack, fin, rec_seq, data = self.parse_segment(ack_message.decode()) # <- expected seq + 2
                    if self.DEBUG: print(f"<-- RECEIVING ACK, seq = {rec_seq} --", end="\n\n")

                    if (syn, ack, fin, rec_seq, data) == (0, 1, 0, self.seq + 2, ""):
                        new_socket.socket_tcp.settimeout(5)
                        new_socket.send_to = self.send_to
                        new_socket.seq = rec_seq
                        if self.DEBUG: 
                            print("--- ESTABLISHED CONNECTION ---")
                            print(self.success_address)
                        return new_socket, self.success_address
                except Exception as e:
                    if self.ERROR_DEBUG: print(f"<-- RECEIVING ACK FAILED, SENDING SYN + ACK AGAIN --", end="\n\n")
                    curr_attemps += 1
                    if MAX_ATTEMPS <= curr_attemps:
                        new_socket.socket_tcp.settimeout(5)
                        new_socket.send_to = self.send_to
                        new_socket.seq = rec_seq 
                        if self.ERROR_DEBUG: 
                            print("--- ESTABLISHED CONNECTION ---")
                            print(self.success_address)
                        self.socket_tcp.close()
                        return new_socket, self.success_address

    def send_using_stop_and_wait(self, message: str):
        self.socket_tcp.settimeout(5)
        # message setup
        encoded_message = message.encode()
        message_length = len(encoded_message)

        # init message setup
        init_message = str(message_length)

        # slicing messages in 16 bytes
        sliced_encoded_message = [encoded_message[i*16:min((i+1)*16, message_length)] for i in range(0, math.ceil(message_length/16))]
        sliced_data = [init_message] + [el.decode() for el in sliced_encoded_message]

        for index, data in enumerate(sliced_data):
            segment = None
            if index == 0:
                segment = self.create_segment(1, 1, 1, self.seq, data) 
            else:
                segment = self.create_segment(0, 0, 0, self.seq, data)
            enconded_segment = segment.encode()
            self.seq = self.seq + 1

            ok = False
            while not ok:
                try:
                    if self.DEBUG: print(f"-- SENDING MESSAGE, seq = {self.seq - 1} -->", end="\n\n")
                    self.socket_tcp.sendto(enconded_segment, self.send_to)
                    ack_message, ad = self.socket_tcp.recvfrom(1024) # self.seq + 1 is needed to continue
                    syn, ack, fin, rec_seq, data = self.parse_segment(ack_message.decode())
                    if self.DEBUG: print(f"<-- RECEIVING ACK, seq = {rec_seq} --", end="\n\n")

                    if (syn, ack, fin, rec_seq, data) == (0, 1, 0, self.seq, ""):
                        ok = True
                except Exception as e:
                    if self.ERROR_DEBUG: print(f"<-- RECEIVING ACK FAILED, SENDING MESSAGE AGAIN --", end="\n\n")

    def recv_using_stop_and_wait(self, buff_size):     
        if len(self.temp) >= buff_size:
            ans = self.temp[:buff_size]
            self.temp = self.temp[buff_size:]
            return ans
        else:
            ok = False
            while not ok:
                try:    
                    em_message, sender_address = self.socket_tcp.recvfrom(1024)
                    syn, ack, fin, rec_seq, data = self.parse_segment(em_message.decode())
                    if self.DEBUG: print(f"<-- RECEIVING MESSAGE, seq = {rec_seq} --", end="\n\n")

                    if (syn, ack, fin, rec_seq, data) == (0, 0, 1, self.seq, ""):
                        if self.DEBUG: print(f"<-- FIN MESSAGE, seq = {rec_seq} --", end="\n\n")
                        fin_ack_message = self.create_segment(0, 1, 1, self.seq + 1, "")
                        MAX_ATTEMPS = 3
                        curr_attemps = 0
                        self.seq = self.seq + 1
                        while True:
                            try:
                                if self.DEBUG: print(f"-- SENDING FIN + ACK, seq = {self.seq} -->", end="\n\n")
                                self.socket_tcp.sendto(fin_ack_message.encode(), self.send_to)

                                
                                ack_message, client_adress = self.socket_tcp.recvfrom(1024)
                                syn, ack, fin, rec_seq, data = self.parse_segment(ack_message.decode()) # <- expected seq + 2
                                if self.DEBUG: print(f"<-- RECEIVING ACK, seq = {rec_seq} --", end="\n\n")

                                if (syn, ack, fin, rec_seq, data) == (0, 1, 0, self.seq + 1, ""):
                                    self.seq = self.seq + 1
                                    self.socket_tcp.close()
                                    if self.DEBUG: print("--- CONNECTION CLOSED ---")
                                    return
                            except Exception as e: 
                                curr_attemps += 1
                                if curr_attemps >= MAX_ATTEMPS:
                                    self.seq = self.seq + 1
                                    self.socket_tcp.close()
                                    if self.ERROR_DEBUG: 
                                        print(f"--- MAXIMUM NUMBER OF ATTEMPTS ACHIEVED ---", end="\n\n")
                                        print("--- CONNECTION CLOSED ---")
                                    return
                                if self.ERROR_DEBUG: print(f"<-- RECEIVING ACK FAILED, TRYING AGAIN --", end="\n\n")
                    if rec_seq == self.seq:
                        if (syn, ack, fin) == (0, 0, 0):
                            self.temp.extend(data.encode())
                            self.message_length = self.message_length - len(data.encode())
                            ok = not (len(self.temp) < buff_size and self.message_length > 0)
                        elif (syn, ack, fin) == (1, 1, 1):
                            self.message_length = int(data)
                        
                        if self.DEBUG: print(f"-- SENDING ACK, seq = {self.seq + 1} -->", end="\n\n")

                        ack_message = self.create_segment(0, 1, 0, self.seq + 1, "")
                        self.socket_tcp.sendto(ack_message.encode(), self.send_to)
                        self.seq = self.seq + 1
                    elif rec_seq < self.seq:
                        if self.DEBUG: print(f"-- REPEATED MESSAGE, SENDING ACK, seq = {self.seq} -->", end="\n\n")

                        ack_message = self.create_segment(0, 1, 0, self.seq, "")
                        self.socket_tcp.sendto(ack_message.encode(), self.send_to)
                except Exception as e:
                    if self.ERROR_DEBUG: print(f"<-- RECEIVING MESSAGE FAILED, TRYING AGAIN --", end="\n\n")

            ans = self.temp[:min(buff_size, len(self.temp))]
            self.temp = self.temp[min(buff_size, len(self.temp)):]
            if self.message_length == 0:
                self.message_length = None
            return ans
            
    def close(self):
        
        seq = self.seq
        syn_message = self.create_segment(0, 0, 1, seq, "")
        MAX_ATTEMPS = 3
        curr_attemps = 0
        while True:
            if self.DEBUG: print(f'-- SENDING FIN, seq = {self.seq} -->', end="\n\n")
            self.socket_tcp.sendto(syn_message.encode(), self.send_to)

            try:
                fin_ack_message, server_adress = self.socket_tcp.recvfrom(1024) 
                syn, ack, fin, rec_seq, data = self.parse_segment(fin_ack_message.decode()) # <- expected seq + 1
                if self.DEBUG: print(f"<-- RECEIVING FIN + ACK, seq = {rec_seq} --", end="\n\n")

                if (syn, ack, fin, rec_seq, data) == (0, 1, 1, seq + 1, ""):
                    for i in range(3):
                        if self.DEBUG: print(f'-- SENDING ACK, seq = {self.seq + 2} -->', end="\n\n")
                        ack_message = self.create_segment(0, 1, 0, seq + 2, "")
                        self.socket_tcp.sendto(ack_message.encode(), self.send_to)
                        time.sleep(5)
                    self.seq = seq + 2

                    if self.DEBUG: print("--- CONNECTION CLOSED ---")
                    self.socket_tcp.close()
                    return
            except Exception as e:
                curr_attemps += 1
                if curr_attemps > MAX_ATTEMPS:
                    if self.ERROR_DEBUG: 
                        print(f"--- MAXIMUM NUMBER OF ATTEMPTS ACHIEVED ---", end="\n\n")
                        print("--- CONNECTION CLOSED ---")
                    self.socket_tcp.close()
                    return
                if self.ERROR_DEBUG: print(f"<-- RECEIVING FIN + ACK FAILED, TRYING AGAIN --", end="\n\n")
        '''
        1. Mandar una segmento con FIN 1
        2. verificar que me llega un mensaje con FIN + ACK (el recv tiene que hacer esto)
        3. Mandar un mensaje ACK de respuesta
        4. Cerrar la conexion
        '''
        pass