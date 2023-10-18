import zmq
import hashlib
import os

# BUF_SIZE es completamente arbitrario, cámbialo según las necesidades de tu aplicación
BUF_SIZE = 1024 * 1024 * 1  # Leemos en fragmentos de 1 MB

sha256 = hashlib.sha256()

def calculate_sha256(data):
    sha256 = hashlib.sha256()
    sha256.update(data.encode('utf-8'))  # Codifica la cadena en bytes
    return sha256.hexdigest()

def connect_to_proxy():
    proxy_ip = input("Ingrese la dirección IP del proxy (por ejemplo, 127.0.0.1): ")
    proxy_port = input("Ingrese el puerto del proxy (por ejemplo, 5555): ")
    proxy_address = f"tcp://{proxy_ip}:{proxy_port}"

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(proxy_address)

    return socket

def upload_file(socket):
    file_path = input("Ingrese el nombre del archivo que desea subir: ")

    print("Calculando SHA256 del archivo...")
    sha256_digest = calculate_sha256(file_path)
    print("SHA256 calculado: {0}".format(sha256_digest))

    socket.send_multipart([b"SHA256", file_path.encode('utf-8'), sha256_digest.encode('utf-8')])
    response = socket.recv_string()
    print("Respuesta del proxy:", response)

    with open(file_path, "rb") as file:
        part_number = 1
        while True:
            file_data = file.read(BUF_SIZE)
            if not file_data:
                break

            part_sha256 = hashlib.sha256(file_data).hexdigest()
            print(f"Enviando parte '{part_number}' del archivo '{file_path}' al proxy...")
            socket.send_multipart([b"PART", part_sha256.encode('utf-8'), file_data, sha256_digest.encode('utf-8')])
            
            response = socket.recv_string()
            print("Respuesta del proxy:", response)
            part_number += 1

    # Enviar una señal de finalización al proxy
    socket.send_multipart([b"END"])
    response = socket.recv_string()
    print("Respuesta del proxy:", response)

def download_file(socket):
    complete_file_sha256 = input("Ingrese el SHA256 del archivo que desea descargar: ")

    # Enviar solicitud al servidor para descargar el archivo con el SHA-256 dado
    socket.send_multipart([b"DOWNLOAD", complete_file_sha256.encode('utf-8')])

    response_parts = socket.recv_multipart()

    if response_parts[0] == b"FILE_NOT_FOUND":
        print("El archivo con el SHA256 dado no existe en el servidor.")
        return

    if response_parts[0] == b"READY_FOR_DOWNLOAD":
        file_name = response_parts[1].decode('utf-8')  # Nombre del archivo
        parts_info = response_parts[2].decode('utf-8')  # Diccionario con los SHA-256 y servidores

        # Convertir el diccionario de cadena a un diccionario Python
        parts_info_dict = eval(parts_info)

        save_folder = "archivos_descargados/"
        os.makedirs(save_folder, exist_ok=True)
        file_path = os.path.join(save_folder, file_name)

        print(f"Descargando archivo '{file_name}' con SHA256: {complete_file_sha256}")

        with open(file_path, "wb") as file:
            part_number = 1

            # Descargar cada parte del archivo desde el servidor correspondiente
            for part_sha256, server_ip_port in parts_info_dict.items():
                server_address = f"{server_ip_port}"

                context = zmq.Context()
                socket_req = context.socket(zmq.REQ)
                socket_req.connect(server_address)

                socket_req.send_multipart([b"REQUEST_PART", part_sha256.encode('utf-8')])
                part_data = socket_req.recv()

                print(f"Recibiendo parte '{part_number}' del archivo desde {server_ip_port}...")
                file.write(part_data)
                part_number += 1

                socket_req.close()

        print(f"El archivo '{file_name}' se ha guardado en '{file_path}'")

    else:
        print("Respuesta inesperada del servidor:", response_parts[0])

def main():
    context = zmq.Context()
    socket = None

    while True:
        print("Menú:")
        print("1. Subir archivo")
        print("2. Descargar archivo")
        print("0. Salir")
        choice = input("Seleccione una opción: ")

        if choice == "1":
            if socket is None:
                socket = connect_to_proxy()
            upload_file(socket)
        elif choice == "2":
            if socket is None:
                socket = connect_to_proxy()
            download_file(socket)
        elif choice == "0":
            break
        else:
            print("Opción no válida. Intente de nuevo.")

    if socket:
        socket.close()

if __name__ == "__main__":
    main()
