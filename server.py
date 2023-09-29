import zmq
import hashlib
import os

sha256 = hashlib.sha256()
STORAGE_SIZE = 1024 * 1024 * input("Ingrese la capacidad del servidor (MB): ")  # Tamaño de 
# Solicitar la dirección IP y el puerto del servidor por consola
server_ip = input("Ingrese la dirección IP del servidor (por ejemplo, 127.0.0.1): ")
server_port = input("Ingrese el puerto del servidor (por ejemplo, 5555): ")

# Construir la dirección del servidor
server_address = f"tcp://{server_ip}:{server_port}"

# Solicitar la dirección IP y el puerto del proxy por consola
proxy_ip = input("Ingrese la dirección IP del proxy (por ejemplo, 127.0.0.1): ")
proxy_port = input("Ingrese el puerto del proxy (por ejemplo, 5555): ")

# Construir la dirección del proxy
proxy_address = f"tcp://{proxy_ip}:{proxy_port}"

# Carpeta donde se guardarán los archivos recibidos
save_folder = "storage/"

def calculate_sha256(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()

def get_storage_usage():
    total_size = 0
    if not os.path.exists(save_folder):
        os.makedirs(save_folder, exist_ok=True)
    for _, _, files in os.walk(save_folder):
        for file in files:
            file_path = os.path.join(save_folder, file)
            total_size += os.path.getsize(file_path)
    return total_size

def register_with_proxy(proxy_address):
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(proxy_address)

        # Envia un mensaje al proxy para registrarse
        socket.send_multipart([b"REGISTER_SERVER", server_address.encode('utf-8')])
        response = socket.recv_string()

        if response == "Server registered":
            print("El servidor se ha registrado con éxito en el proxy.")
        else:
            print("Error al registrar el servidor en el proxy.")

        socket.close()
    except Exception as e:
        print(f"Error al registrar el servidor en el proxy: {str(e)}")

def main():
    # Registra el servidor con el proxy al inicio
    register_with_proxy(proxy_address)
    
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(server_address)

    print("Esperando la conexión del cliente...")
    

    while True:
        message = socket.recv_multipart()

        if message[0] == b"PART":
            # Recibimos una parte del archivo
            part_sha256 = message[1]
            part_data = message[2]

            # Calcula el tamaño actual del almacenamiento
            storage_usage = get_storage_usage()

            # Verifica si hay suficiente espacio para la parte recibida
            if storage_usage + len(part_data) <= STORAGE_SIZE:
                # Guardamos la parte en disco con el nombre como su sha256 parcial
                part_filename = os.path.join(save_folder, part_sha256.decode('utf-8'))
                with open(part_filename, 'wb') as f:
                    f.write(part_data)
                print(f"PART {part_sha256.decode('utf-8')} received")
                socket.send_string(f"PART received")
            else:
                print("El servidor no tiene suficiente espacio de almacenamiento.")
                socket.send_string("INSUFFICIENT_STORAGE")

        elif message[0] == b"REQUEST_PART":
            # Cliente solicita una parte específica del archivo
            part_sha256 = message[1].decode('utf-8')
            part_filename = os.path.join(save_folder, part_sha256)
            
            if os.path.isfile(part_filename):
                with open(part_filename, 'rb') as f:
                    part_data = f.read()
                    socket.send(part_data)
            else:
                # La parte solicitada no existe en el servidor
                socket.send(b"PART_NOT_FOUND")

if __name__ == "__main__":
    main()
