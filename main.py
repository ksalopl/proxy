import socket
import sys
from _thread import *
import select, queue


max_connection = 20
buffer_size = 8192
listening_port = 8000

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', listening_port))
    server.listen(max_connection)

    print("Server started successfully [ %d ]" %(listening_port))

    while True:
        try:
            connection, address = server.accept()
            start_new_thread(conn_string, (connection,))
            print('New user just connected to me [ %s, %d ]' % address)
        except KeyboardInterrupt:
            server.close()
            print("\n Shutdown")
            sys.exit(1)


def take_first_line(connection):
    data = b''
    while True:
        chunk = connection.recv(1024)
        data += chunk

        if b'\r\n\r\n' in data:
            return data


def conn_string(conn):
    target = None

    try:
        first_line_data = take_first_line(conn)
        first_line = first_line_data.split(b'\r', 1)[0].decode()
        method, uri, _ = first_line.split(None, 2)

        parts = uri.split('://', 1)

        protocol = None
        url = None


        if len(parts) > 1:
            protocol = parts[0]
            url = parts[1]
        else:
            url = parts[0]


        url = url.split('/', 1)[0]
        parts = url.split(':', 1)

        port = 80

        if len(parts) > 1:
            url = parts[0]
            port = parts[1]
        else:
            url = parts[0]

        print('User want to [ %s, %s ]' % (url, port))

        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((url, int(port)))

        if method != 'CONNECT':
            target.sendall(first_line_data)
        else:
            conn.sendall(b'HTTP/1.1 200 OK\r\n\r\n')

        make_tunnel(conn, target)
        conn.close()
        target.close()

    except Exception as e:
        print(e)
        conn.close()

        if target:
            target.close()


def make_tunnel(receiver, provider):
    l = [receiver, provider]

    receiver.setblocking(False)
    provider.setblocking(False)

    data_for_receiver = queue.Queue()
    data_for_provider = queue.Queue()

    while True:
        reads, sends, breakable = select.select(l, l, l)

        for r in reads:
            if r is receiver:
                data = r.recv(buffer_size)
                print('Receiver receive %d' % (len(data),))

                if not data:
                    print('Receiver stop')
                    return

                data_for_provider.put(data)

            if r is provider:
                data = r.recv(buffer_size)
                print('Provider receive %d' % (len(data),))

                if not data:
                    print('Provider stop')
                    return

                data_for_receiver.put(data)

        for s in sends:
            if s is receiver and not data_for_receiver.empty():
                data = data_for_receiver.get_nowait()
                print('Send data to Receiver %d' % (len(data),))
                s.sendall(data)

            if s is provider and not data_for_provider.empty():
                data = data_for_provider.get_nowait()
                print('Send data to Provider %d' % (len(data),))
                s.sendall(data)

        if len(breakable) > 0:

            if receiver in breakable:
                print('Break on Receiver')

            if provider in breakable:
                print('Break on Provider')

            return


if __name__== "__main__":
    start()
