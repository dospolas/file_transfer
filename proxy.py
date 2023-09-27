import zmq
import hashlib
import os

sha256 = hashlib.sha256()

# Solicitar la dirección IP y el puerto del proxy por consola
proxy_ip = input("Ingrese la dirección IP del proxy (por ejemplo, 127.0.0.1): ")
proxy_port = input("Ingrese el puerto del proxy (por ejemplo, 5555): ")

# Construir la dirección del proxy
proxy_address = f"tcp://{proxy_ip}:{proxy_port}"

def calculate_sha256(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()

def main():
    context = zmq.Context()
    socket_rep = context.socket(zmq.REP)
    socket_rep.bind(proxy_address)

    print("Esperando la conexión del cliente...")
    
    # Variables para mantener el registro de partes y el sha256 del archivo completo
    file_sha256_parts = {}
    file_paths = {}
    complete_file_sha256 = None
    registered_servers = []
    iterator = 0

    while True:
        message = socket_rep.recv_multipart()

        if message[0] == b"SHA256":
            # Recibimos el sha256 del archivo completo como bytes (b)
            file_path = message[1]
            complete_file_sha256 = message[2]
            #Añade el file_path a un dicionario que permita referenciar el sha256 completo
            file_paths[complete_file_sha256] = file_path
            socket_rep.send_string("SHA256 received")

        elif message[0] == b"REGISTER_SERVER":
            server_ip_port = message[1].decode('utf-8')
            if server_ip_port not in registered_servers:
                registered_servers.append(server_ip_port)
            print(f"Servidor Registrado -- {server_ip_port}")
            socket_rep.send_string("Server registered")

        elif message[0] == b"PART":
            # Recibimos una parte del archivo
            part_sha256 = message[1]
            part_data = message[2]

            # Variable para rastrear si alguna parte se guardó con éxito
            part_saved = False

            while True:
                # Crea un socket REQ para comunicarse con el servidor
                context = zmq.Context()
                socket_req = context.socket(zmq.REQ)
                socket_req.connect(f"tcp://{registered_servers[iterator]}")

                # Envía la parte al servidor
                socket_req.send_multipart([b"PART", part_sha256, part_data])

                # Espera una respuesta del servidor
                response = socket_req.recv_string()

                # Si el servidor confirma la recepción, marca la parte como guardada
                if response == "PART received":
                    part_saved = True

                # Cierra el socket REQ
                socket_req.close()
                iterator = (iterator + 1) % len(registered_servers)

                # Si la parte se guardó con éxito en algún servidor, sale del bucle
                if part_saved:
                    # Agregamos el sha256 parcial al diccionario correspondiente
                    if complete_file_sha256:
                        if complete_file_sha256 not in file_sha256_parts:
                            file_sha256_parts[complete_file_sha256] = {}
                        file_sha256_parts[complete_file_sha256][part_sha256.decode('utf-8')] = server_ip_port #IP y puerto del server donde se guardo

                    break

            # Envía una respuesta al cliente
            print(file_sha256_parts)     
            print(f"PART {part_sha256.decode('utf-8')} received")
            socket_rep.send_string(f"PART {part_sha256.decode('utf-8')} received")

        elif message[0] == b"END":
            # El cliente ha terminado de enviar partes
            print(f"FILE {complete_file_sha256.decode('utf-8')} completed")
            socket_rep.send_string("END received")

if __name__ == "__main__":
    main()
