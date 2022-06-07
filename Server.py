#! /usr/bin/env python
#====================== Bibliotecas =================================================
import socket #Biblioteca para comunicaçãp
import sys #Biblioteca para manipular o ambiente 
import threading #Biblioteca para controlar os fluxos de programa
import select
import traceback #Biblioteca para manipular as pilhas
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

SOCKET_LIST = []
TO_BE_SENT = []
SENT_BY = {}
KEYS = {}
#====================== Classe =================================================
class CryptASSYN:
    def __init__(self):
        self.myPublicKey = 0
        self.myPrivateKey = 0
        self.prKeySerial = 0
        self.puKeySerial = 0

    def geraChaves(self):    
        self.myPrivateKey = rsa.generate_private_key( #Geração da chave privada
            public_exponent=65537, #Metodo matemático para gerar chave,
            key_size=2048,) #Tamanho da chave em bits, 2048 é seguro)
       
        self.myPublicKey = self.myPrivateKey.public_key() #A partir da chave privada, deriva-se a chave pública
        self.puKeySerial = self.myPublicKey.public_bytes( #Serialização da chave publica
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)

        self.prKeySerial = self.myPrivateKey.private_bytes( #Serialização da chave privada
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(b'mypassword'))

    def cryptKey(self, key, publicKeyServer):  
        #signature = self.myPrivateKey.sign( #Gera a assinatura da mensagem com a chave privada
        #    key,
        #    padding.PSS(
        #       mgf=padding.MGF1(hashes.SHA256()),
        #       salt_length=padding.PSS.MAX_LENGTH),
        #    hashes.SHA256())
        keyCrp =  publicKeyServer.encrypt( #Criptografa a chave síncrona
            key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None))
        return keyCrp

    def descryptKey(self, key2Crp):
        key = self.myPrivateKey.decrypt(
            key2Crp,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None))
        return key
#====================== Classe =================================================
class Server(threading.Thread):

    def init(self):
        self.myKey = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.bind(('', 5535))
        self.sock.listen(2)
        SOCKET_LIST.append(self.sock)
        print("Server started on port 5535")

    def run(self):
        while 1:
            read, write, err = select.select(SOCKET_LIST, [], [], 0)
            marcador = 0 #Indicador quando chega a chave síncrona codificada
            for sock in read:
                if sock == self.sock:
                    sockfd, addr = self.sock.accept()
                    print(str(addr))
                    SOCKET_LIST.append(sockfd)
                    print(SOCKET_LIST[len(SOCKET_LIST) - 1])
                else:
                    try: #Guarda e marca as mensagens à serem enviadas
                        sock.send(crAS.puKeySerial) #Envia a chave pública do servidor para o cliente
                        s = sock.recv(1024) #Recebe a mensagem
                        if b'-----BEGIN' and b"KEY-----" in s: #Verifica se é a chave pública do cliente
                            KEYS[sock.getpeername()] = s #Guarda a chave no lugar correspondente [1]
                        else: #Caso não seja a chave...
                            if s == '': #Verifica se a mensagem está vazia
                                print(str(sock.getpeername())) #Imprime quem enviou nada
                                continue
                            elif marcador == 0: #Chave codificada chegou
                                self.myKey = crAS.descryptKey(s) #Descriptografa a chave síncrona com a chave pública do servidor
                                for keys, values in KEYS.items(): #Para cada usuário...
                                    keyCod = crAS.cryptKey(values, serialization.load_pem_public_key( #Deserializa a chava pública do servidor...
                                        srv.publicKeyServer)) #Codifica a chave síncrona com a publica do Servidor
                                    keys.send(keyCod) #Envia a chave
                                marcador = 1 #Zera o marcador pra próxima vês
                            else: #Caso seja a mensagem...
                                TO_BE_SENT.append(s) #Guarda a mensagem para enviar posteriomente
                                SENT_BY[s] = (str(sock.getpeername())) #Marca de quem é a mensagem
                                self.marcador = 0 #A próxima mensagem é a chave codificada
                    except:
                        print(str(sock.getpeername()))

#====================== Classe =================================================
class handle_connections(threading.Thread):
    def run(self):
        while 1:
            read, write, err = select.select([], SOCKET_LIST, [], 0)
            for items in TO_BE_SENT: #Para cada mensagem, que precisa ser enviada...
                for s in write: #Para cada pessoa na transmissão...
                    try:
                        if (str(s.getpeername()) == SENT_BY[items]): #Ignora o próprio emissor da mensagem
                            print("Ignoring %s" % (str(s.getpeername()))) 
                            continue
                        print("Sending to %s" % (str(s.getpeername())))
                        s.send(items) #Envia a mensagem
                    except:
                        traceback.print_exc(file=sys.stdout)
                TO_BE_SENT.remove(items)
                del (SENT_BY[items])


if __name__ == '__main__':
    crAS = CryptASSYN() #Cria um objeto chamado "crAS" da classe CryptASSYN
    crAS.geraChaves()
    srv = Server()
    srv.init()
    srv.start()
    print(SOCKET_LIST)
    handle = handle_connections()
    handle.start()