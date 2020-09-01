import json
import os
import socket
import threading
import time
import selectors


class Network:
    def __init__(self, network_topology):
        self.nodes = []
        nodes_id = []
        for i in network_topology:
            nodes_id.append(i[0])
        for i in range(len(network_topology)):
            node_id = network_topology[i][0]
            ip = network_topology[i][1]
            port = network_topology[i][2]
            neighbor_id = network_topology[i][3]
            link_delay = network_topology[i][4]
            file_list = network_topology[i][5]
            neighbor_ip = []
            neighbor_port = []
            for temp_id in neighbor_id:
                k = nodes_id.index(temp_id)
                neighbor_ip.append(network_topology[k][1])
                neighbor_port.append(network_topology[k][2])
            neighbor = self.neighbor_maker(neighbor_id, neighbor_ip, neighbor_port, link_delay)
            self.nodes.append(Node(node_id, ip, port, neighbor, file_list))

    def init_network(self):
        for node in self.nodes:
            node.init_node()

    def node_finder(self, node_id):
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def file_request(self, node_id, file_name):
        node = self.node_finder(node_id)
        if node:
            return node.file_request(file_name)
        else:
            return 'failed'

    def delete_node(self, node_id):
        node = self.node_finder(node_id)
        if node:
            self.nodes.remove(node)
            node.close_node()
            s = 'file with node_id = {} deleted successfully'
            print(s.format(node_id))
        else:
            s = 'file with node_id = {} not found'
            print(s.format(node_id))

    @staticmethod
    def neighbor_maker(neighbors_id, neighbors_ip, neighbors_port, link_delay):
        neighbor = []
        for i in range(len(neighbors_id)):
            neighbor.append(dict(id=neighbors_id[i], ip=neighbors_ip[i],
                                 port=neighbors_port[i], delay=link_delay[i]))
        return neighbor

    def add_node(self, node_id, node_ip, node_port, neighbors_id,
                 neighbors_ip, neighbors_port, link_delay):
        neighbor = self.neighbor_maker(neighbors_id, neighbors_ip, neighbors_port, link_delay)
        node = Node(node_id, node_ip, node_port, neighbor, [])
        self.nodes.append(node)
        node.init_node()

    def add_file(self, node_id, file_name):
        node = self.node_finder(node_id)
        if node:
            node.add_file(file_name)

    def remove_file(self, node_id, file_name):
        node = self.node_finder(node_id)
        if node:
            node.remove_file(file_name)

    def close(self):
        for node in self.nodes:
            node.close_node()


class Node:
    def __init__(self, node_id='', ip='127.0.0.1', port=43000, neighbor_nodes=None, file_list=None):
        self.id = node_id
        self.ip = ip
        self.port = port
        self.neighborNodes = neighbor_nodes
        self.fileList = file_list.copy()
        self.file_list_lock = threading.Lock()
        for file in file_list:
            self.add_file(file)
        self.thread_server = threading.Thread(target=self.run_node_server, args=())
        self.thread_client = threading.Thread(target=self.run_node_client, args=())
        self.event_close = threading.Event()
        self.event_init_finished = threading.Event()
        self.networking = NodeNetworking(self)
        self.neighbor_access_lock = threading.Lock()

    def init_node(self):
        for neighbor in self.neighborNodes:
            neighbor['ttl'] = 10
        self.thread_server.start()
        self.event_init_finished.wait()
        self.event_init_finished.clear()
        self.thread_client.start()
        self.event_init_finished.wait()

    def file_request(self, file_name):
        event = threading.Event()
        self.networking.networking_request_file(file_name, event)
        event.wait(10)
        if event.is_set():
            return 'success'
        else:
            return 'failed'

    def add_file(self, file_name):
        self.file_list_lock.acquire()
        self.fileList.append(file_name)
        self.file_list_lock.release()
        try:
            os.makedirs(str(self.id))
        except FileExistsError:
            pass
        file = open(str(self.id) + '/' + file_name, 'w')
        file.close()

    def add_file_data(self, file_name, file_data):
        self.fileList.append(file_name)
        try:
            os.makedirs(str(self.id))
        except FileExistsError:
            pass
        file = open(str(self.id) + '/' + file_name, 'w')
        file.write(file_data)
        file.close()

    def remove_file(self, file_name):
        self.fileList.remove(file_name)
        if os.path.exists(str(self.id) + '/' + file_name):
            os.remove(str(self.id) + '/' + file_name)

    def read_file_data(self, file_name):
        file = open(str(self.id) + '/' + file_name, 'r')
        data = file.read()
        file.close()
        return data

    def close_node(self):
        self.event_close.set()
        self.networking.networking_end()
        self.thread_server.join()
        self.thread_client.join()

    def run_node_server(self):
        self.networking.networking_init('', self.port)  # init mode
        self.event_init_finished.set()
        self.networking.networking_listen()  # normal
        self.networking.networking_end()  # closing mode

    def run_node_client(self):
        self.networking.task_hello_neighbors(self.get_neighbors())
        self.event_init_finished.set()
        while not self.event_close.is_set():
            ping_needed_neighbors = self.decrease_neighbors_ttl()
            not_responded_neighbors = self.networking.task_ping_neighbors(ping_needed_neighbors)
            self.remove_not_responding_neighbors(not_responded_neighbors)
            for neighbor in ping_needed_neighbors:
                if not not_responded_neighbors.__contains__(neighbor):
                    self.change_neighbor_ttl(neighbor, 10)
            self.event_close.wait(1)

    def remove_not_responding_neighbors(self, not_responding_neighbors):
        self.neighbor_access_lock.acquire()
        for not_responding_neighbor in not_responding_neighbors:
            if not_responding_neighbor['ttl'] <= 0:
                self.neighborNodes.remove(not_responding_neighbor)
        self.neighbor_access_lock.release()

    def get_neighbors(self):
        self.neighbor_access_lock.acquire()
        neighbors = self.neighborNodes.copy()
        self.neighbor_access_lock.release()
        return neighbors

    def change_neighbor_ttl(self, neighbor, ttl):
        self.neighbor_access_lock.acquire()
        neighbor['ttl'] = ttl
        self.neighbor_access_lock.release()

    def decrease_neighbors_ttl(self):
        ping_needed_neighbors = []
        neighbors = self.get_neighbors()
        for neighbor in neighbors:
            if neighbor['ttl'] > 0:
                neighbor['ttl'] -= 1
            else:
                ping_needed_neighbors.append(neighbor)
        return ping_needed_neighbors

    def match_or_add_neighbor(self, neighbor_id, neighbor_ip, neighbor_port, neighbor_delay):
        neighbor = self.match_neighbor(neighbor_id)
        if neighbor:
            return neighbor
        else:
            neighbor = {'id': neighbor_id, 'ip': neighbor_ip, 'port': neighbor_port,
                        'delay': neighbor_delay}
            self.neighbor_access_lock.acquire()
            self.neighborNodes.append(neighbor)
            self.neighbor_access_lock.release()
            return neighbor

    def match_neighbor(self, neighbor_id):
        neighbors = self.get_neighbors()
        for neighbor in neighbors:
            if neighbor['id'] == neighbor_id:
                return neighbor
        return None

    def match_file_name(self, file_name):
        self.file_list_lock.acquire()
        res = self.fileList.__contains__(file_name)
        self.file_list_lock.release()
        return res


class NodeNetworking:
    def __init__(self, node):
        self.node = node
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.selectors = selectors.DefaultSelector()
        self.threads = []
        self.query_id = 0
        self.query_event = []
        self.query_lock = threading.Lock()
        self.flood_buffer = []
        self.flood_buffer_lock = threading.Lock()

    def networking_init(self, ip, port):
        self.socket.bind((ip, port))
        self.socket.listen(5)
        self.socket.setblocking(False)
        self.selectors.register(self.socket, selectors.EVENT_READ, )

    def networking_end(self):
        for thread in self.threads:
            thread.join()
        self.socket.close()

    def networking_request_file(self, file_name, event):
        self.query_lock.acquire()
        self.query_event.append(event)
        query_id = self.query_id
        self.query_id += 1
        self.query_lock.release()
        message_maker = Message()
        neighbors = self.node.get_neighbors()
        for neighbor in neighbors:
            socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
            if not socket_obj:
                continue
            msg = message_maker.message_file_query(self.node.id, self.node.ip, self.node.port, neighbor['delay'],
                                                   [self.node.id], file_name, 5, query_id)
            self.networking_send(socket_obj, neighbor['delay'], msg,)
            socket_obj.close()

    def task_hello_neighbors(self, neighbors):
        lock = threading.Lock()
        for neighbor in neighbors:
            thread = threading.Thread(target=self.task_hello_neighbor, args=(neighbor, lock))
            self.threads.append(thread)
            thread.start()

    def task_hello_neighbor(self, neighbor, lock):
        message_maker = Message()
        message = message_maker.message_hello(self.node.id, self.node.ip, self.node.port, neighbor['delay'])
        socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
        if socket_obj:
            self.networking_send(socket_obj, neighbor['delay'], message, )
            socket_obj.close()
        lock.acquire()
        self.threads.remove(threading.current_thread())
        lock.release()

    def networking_listen(self):
        while not self.node.event_close.is_set():
            events = self.selectors.select(0.1)
            for key, event in events:
                if (event and selectors.EVENT_READ) and (not key.data):
                    thread = threading.Thread(target=self.answer_processing, args=(key.fileobj,))
                    self.threads.append(thread)
                    thread.start()

    def networking_send(self, socket_obj=socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                        delay=0, message='', wait=0.1):
        time.sleep(delay)
        try:
            # time_out = socket_obj.gettimeout()
            socket_obj.settimeout(wait)
            socket_obj.sendall(message.encode('utf8'))
            # socket_obj.settimeout(time_out)
            print('message sent from ' + str(self.node.id) + ': ' + message)
        except socket.error:
            print('message sent error from ' + str(self.node.id) + ': ' + message)

    def networking_receive(self, socket_obj=socket.socket(socket.AF_INET, socket.SOCK_STREAM), wait=0.1):
        try:
            # time_out = socket_obj.gettimeout()
            socket_obj.settimeout(wait)
            data = socket_obj.recv(1024)
            # socket_obj.settimeout(time_out)
            message = data.decode('utf8')
            print('message receive from ' + str(self.node.id) + ': ' + message)
            return message
        except socket.error:
            print('message receive error from ' + str(self.node.id))
            return ''

    def networking_connect(self, ip, port):
        try:
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_obj.settimeout(0.1)
            socket_obj.connect((ip, port))
            return socket_obj
        except socket.error:
            print('connection error from ' + str(self.node.id) + ' to ' + ip + ':' + str(port))
            return None

    def answer_processing(self, socket_key):
        if self.node.event_close.is_set():
            return
        connection, address = socket_key.accept()
        # connection, address = self.socket.accept()
        message_maker = Message()
        msg = self.networking_receive(connection, 10)
        if msg:
            msg = message_maker.loads(msg)
            if msg['type'] == 'Ping':
                self.task_pong(msg, connection)
                connection.close()
            if msg['type'] == 'Hello':
                connection.close()
                self.task_hello(msg)
            if msg['type'] == 'FileQuery':
                connection.close()
                self.task_file_query(msg)
            if msg['type'] == 'FileFounded':
                connection.close()
                self.task_file_founded(msg)
        self.threads.remove(threading.current_thread())
        pass

    def task_ping_neighbors(self, neighbors):
        not_responding = []
        lock = threading.Lock()
        threads = []
        for neighbor in neighbors:
            thread = threading.Thread(target=self.task_ping, args=(neighbor, not_responding, lock))
            threads.append(thread)
            self.threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
            self.threads.remove(thread)
        return not_responding

    def task_ping(self, neighbor, not_responding, lock):
        socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
        if not socket_obj:
            lock.acquire()
            not_responding.append(neighbor)
            lock.release()
            return neighbor
        message_maker = Message()
        msg = message_maker.message_ping(self.node.id, self.node.ip, self.node.port, neighbor['delay'])
        self.networking_send(socket_obj, neighbor['delay'], msg)
        msg = self.networking_receive(socket_obj, 1.5 * neighbor['delay'])
        if not msg:
            lock.acquire()
            not_responding.append(neighbor)
            lock.release()
            return neighbor
        msg = message_maker.loads(msg)
        if msg['id'] != neighbor['id']:
            lock.acquire()
            not_responding.append(neighbor)
            lock.release()
            return neighbor
        return None

    def task_pong(self, ping_message, connection):
        neighbor = self.node.match_or_add_neighbor(ping_message['id'], ping_message['ip'],
                                                   ping_message['port'], ping_message['delay'])
        self.neighbor_update(neighbor, ping_message)
        message_maker = Message()
        msg = message_maker.message_pong(self.node.id, self.node.ip, self.node.port, neighbor['delay'])
        self.networking_send(connection, neighbor['delay'], msg, )

    def task_hello(self, hello_message):
        neighbor = self.node.match_or_add_neighbor(hello_message['id'], hello_message['ip'],
                                                   hello_message['port'], hello_message['delay'])
        self.neighbor_update(neighbor, hello_message)

    def neighbor_update(self, neighbor, message):
        neighbor['ip'] = message['ip']
        neighbor['port'] = message['port']
        neighbor['delay'] = message['delay']
        self.node.change_neighbor_ttl(neighbor, 10)

    def task_file_founded(self, file_founded_message):
        neighbor = self.node.match_or_add_neighbor(file_founded_message['id'], file_founded_message['ip'],
                                                   file_founded_message['port'], file_founded_message['delay'])
        self.neighbor_update(neighbor, file_founded_message)
        if not file_founded_message['path']:
            self.node.add_file_data(file_founded_message['file_name'], file_founded_message['file_data'])
            self.node.file_list_lock.acquire()
            self.node.fileList.append(file_founded_message['file_name'])
            self.node.file_list_lock.release()
            self.query_lock.acquire()
            self.query_event[file_founded_message['query_id']].set()
            self.query_lock.release()
            return
        neighbor_id = file_founded_message['path'].pop()
        neighbor = self.node.match_neighbor(neighbor_id)
        if not neighbor:
            return
        file_founded_message['id'] = self.node.id
        file_founded_message['ip'] = self.node.ip
        file_founded_message['port'] = self.node.port
        file_founded_message['delay'] = neighbor['delay']
        socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
        if not socket_obj:
            return
        message_maker = Message()
        message_maker.payload = file_founded_message
        self.networking_send(socket_obj, neighbor['delay'], message_maker.dump(), )
        socket_obj.close()

    def task_file_query(self, file_query_message):
        message_maker = Message()
        neighbor = self.node.match_or_add_neighbor(file_query_message['id'], file_query_message['ip'],
                                                   file_query_message['port'], file_query_message['delay'])
        self.neighbor_update(neighbor, file_query_message)
        if file_query_message['ttl'] <= 1:
            return
        file_query_message['ttl'] -= 1
        if not self.match_flood_buffer(file_query_message):
            return
        if self.node.match_file_name(file_query_message['file_name']):
            file_query_message['path'].pop()
            msg = message_maker.message_file_founded(self.node.id, self.node.ip, self.node.port, neighbor['delay'],
                                                     file_query_message['path'], file_query_message['file_name'],
                                                     self.node.read_file_data(file_query_message['file_name']),
                                                     file_query_message['query_id'])
            socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
            if not socket_obj:
                return
            self.networking_send(socket_obj, neighbor['delay'], msg,)
            socket_obj.close()
            return
        neighbors = self.node.get_neighbors()
        neighbors.remove(neighbor)
        file_query_message['id'] = self.node.id
        file_query_message['ip'] = self.node.ip
        file_query_message['port'] = self.node.port
        file_query_message['delay'] = neighbor['delay']
        file_query_message['path'].append(self.node.id)
        for neighbor in neighbors:
            socket_obj = self.networking_connect(neighbor['ip'], neighbor['port'])
            if not socket_obj:
                continue
            message_maker.payload = file_query_message
            self.networking_send(socket_obj, neighbor['delay'], message_maker.dump(), )
            socket_obj.close()

    def match_flood_buffer(self, file_query_message):
        self.flood_buffer_lock.acquire()
        flood_buffer = self.flood_buffer.copy()
        self.flood_buffer_lock.release()
        source_id = file_query_message['path'][0]
        for flood in flood_buffer:
            if flood['source_id'] == source_id:
                if flood['query_id'] < file_query_message['query_id']:
                    flood['query_id'] = file_query_message['query_id']
                    return True
                else:
                    return False
        self.flood_buffer_lock.acquire()
        self.flood_buffer.append({'source_id': source_id, 'query_id': file_query_message['query_id']})
        self.flood_buffer_lock.release()
        return True


class Message:
    def __init__(self):
        self.payload = {}

    def dump(self):
        return json.dumps(self.payload)

    def loads(self, message):
        self.payload = json.loads(message)
        return self.payload

    def message_hello(self, node_id, ip, port, delay):
        self.payload = {'type': 'Hello', 'id': node_id, 'ip': ip, 'port': port, 'delay': delay}
        return self.dump()

    def message_file_query(self, node_id, ip, port, delay, path, file_name, ttl, query_id):
        self.payload = {'type': 'FileQuery', 'id': node_id, 'ip': ip, 'port': port,
                        'delay': delay, 'path': path, 'file_name': file_name, 'ttl': ttl, 'query_id': query_id}
        return self.dump()

    def message_file_founded(self, node_id, ip, port, delay, path, file_name, file_data, query_id):
        self.payload = {'type': 'FileFounded', 'id': node_id, 'ip': ip, 'port': port,
                        'delay': delay, 'path': path, 'file_name': file_name,
                        'file_data': file_data, 'query_id': query_id}
        return self.dump()

    def message_file_containing(self):
        pass
        return self.dump()

    def message_ping(self, node_id, ip, port, delay):
        self.payload = {'type': 'Ping', 'id': node_id, 'ip': ip, 'port': port, 'delay': delay}
        return self.dump()

    def message_pong(self, node_id, ip, port, delay):
        self.payload = {'type': 'Pong', 'id': node_id, 'ip': ip, 'port': port, 'delay': delay}
        return self.dump()

    def message_fail(self):
        pass
        return self.dump()


if __name__ == '__main__':
    graph_topology = [[0, '127.0.0.1', 43000, [1], [1], ['a']], [1, '127.0.0.1', 43001, [0], [1], ['b']],
                      [2, '127.0.0.1', 43002, [0, 1], [1, 1], ['c']], [4, '127.0.0.1', 43003, [1], [1], ['d']]]
    network = Network(graph_topology)
    network.init_network()
    """
    for l in range(4):
        time.sleep(3)
        print(network.nodes[0].get_neighbors())
        """
    time.sleep(2)
    print(network.file_request(0, 'd'))
    network.remove_file(0, 'd')
    network.delete_node(0)
    time.sleep(10)
    print(network.file_request(2,'a'))
    time.sleep(15)
    network.add_node(0, '127.0.0.1', 43000, [1], ['127.0.0.1'], [43001], [1])
    network.add_file(0, 'a')
    time.sleep(3)
    print(network.file_request(2, 'a'))
    network.close()
    for node_1 in network.nodes:
        node_1.thread_client.join()
        node_1.thread_server.join()
