import time
import socket
import threading
import json
import random


class BattleGround:
    def __init__(self, _x, _y):
        self.x = _x
        self.y = _y

TTL = 1000
p = 1.1
t = 0

class TableEntry:
    def __init__(self, _key, _nxt_hop, _time_to_live, _seq_num ):
        self.key = _key
        self.nxt_hop = _nxt_hop
        self.time_to_live = _time_to_live
        self.seq_num = _seq_num

    def print_entry(self):
        print("key: " + str(self.key) + " next hop: " + str(self.nxt_hop))

class Message:
    def __init__(self, nid, type, value):
        self.nid = nid
        self.type = type # hello , hello_ack , Message
        self.value = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class Vehicle:
    def __init__(self, _id, _x, _y, _ip, _port, _delay, _server_ip, _server_port, _battle_ground, _n):
        self.id = _id
        self.x = _x
        self.y = _y
        self.ip = _ip
        self.port = _port
        self.server_ip = _server_ip
        self.server_port = _server_port
        self.server_conn = []
        self.battle_ground = _battle_ground
        self.delay = _delay
        self.n = _n
        self.route_table = []
        self.init_finish = False
        self.nbrs = []
        self.rrq_received = []
        self.rrq_counter = 1

        self.recently_sent = [0]

        main_thread = threading.Thread(target=self.main, args=())
        main_thread.daemon = True
        main_thread.start()

    def main(self):

        server_thread = threading.Thread(target=self.listen_to_server, args=())
        server_thread.daemon = True
        server_thread.start()

        time.sleep(0.25 * self.n)

        connect_thread = threading.Thread(target=self.connect_to_server, args=())
        connect_thread.daemon = True
        connect_thread.start()

    def delayed_send(self, msg):
        self.recently_sent[0] = msg

        byte_array = json.dumps(msg.__dict__).encode("utf-8")
        time.sleep(self.delay)
        self.server_conn[0].send(byte_array)

    def connect_to_server(self):

        client_socket = socket.socket()
        client_socket.connect((self.server_ip, self.server_port))
        self.server_conn.append(client_socket)

        hello_thread = threading.Thread(target=self.hello, args=())
        hello_thread.daemon = True
        hello_thread.start()

    def listen_to_server(self):
        server_socket = socket.socket()
        server_socket.bind((self.ip, self.port))
        server_socket.listen(2)
        conn, address = server_socket.accept()
        while True:
            data = conn.recv(1024)
            if not data:
                break
            else:
                msg_rec = Message(**json.loads(data, encoding="utf-8"))

                if msg_rec.type == "hello":
                    m = Message(str(self.id), "hello_ack", msg_rec.nid)
                    delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                    delayed_send_thread.daemon = True
                    delayed_send_thread.start()

                elif msg_rec.type == "hello_ack":
                    self.route_table.append(TableEntry(int(msg_rec.nid), int(msg_rec.nid), TTL, 0 ))
                    print("update " + str(self.id) + " Routing table of node " + str(self.id))

                elif msg_rec.type == "init_finish":
                    self.init_finish = True

                elif msg_rec.type == "RRQ":
                    #  destination ----------- counter
                    tmp2 = msg_rec.value.split("+")
                    # current hop --------- source
                    tmp3 = msg_rec.nid.split("+")

                    # check for duplicate rrq
                    found = False
                    for item4 in self.rrq_received:
                        if item4[0] == tmp3[1] and item4[1] == tmp2[0] and item4[2] == tmp2[1]:
                            found = True
                            break
                    if found:
                        continue
                    else:
                        # source -------------- destination ----------- counter
                        self.rrq_received.append([tmp3[1], tmp2[0], tmp2[1]])

                        # update routing
                        founded = False
                        for item7 in self.route_table:
                            if str(item7.key) == str(tmp3[1]):
                                founded = True
                                break
                        if founded:
                           pass
                        else:
                            self.route_table.append(TableEntry(int(tmp3[1]), int(tmp3[0]), TTL, int(tmp2[1])))
                            print("update " + str(self.id) + " Routing table of node " + str(self.id))

                        # check if dst
                        rrp = 0
                        if int(tmp2[0]) == self.id:
                            rrp = self.id
                        # in routing table
                        for item5 in self.route_table:
                            if item5.key == int(tmp2[0]):
                                rrp = item5.nxt_hop
                        if rrp:
                            # relay back rrp
                            # current --------------- next hop ---------------- source -------------- destination
                            m = Message(str(self.id) + "+" + str(tmp3[0]), "RRP", str(tmp3[1]) + "+" + str(tmp2[0]))
                            delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                            delayed_send_thread.daemon = True
                            delayed_send_thread.start()

                        else:
                            # rebroadcast RRQ
                            m = Message(str(self.id) + "+" + str(tmp3[1]), "RRQ", msg_rec.value)
                            self.rrq_counter = self.rrq_counter + 1
                            delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                            delayed_send_thread.daemon = True
                            delayed_send_thread.start()

                elif msg_rec.type == "RRP":
                    tmp2 = msg_rec.value.split("+")

                    # add to routing table

                    already_existed = False
                    for item5 in self.route_table:
                        if item5.key == int(tmp2[1]):
                            already_existed = True
                    if already_existed:
                        pass
                    else:
                        self.route_table.append(TableEntry(int(tmp2[1]), int(msg_rec.nid), TTL, 0))
                        print("update " + str(self.id) + " Routing table of node " + str(self.id))

                    # if source, send message, else relay back
                    if int(tmp2[0]) == self.id:
                        pass
                    else:
                        # search in routing table
                        tmp4 = 0
                        for item5 in self.route_table:
                            if item5.key == int(tmp2[0]):
                                tmp4 = item5.nxt_hop

                        # relay back rrp
                        m = Message(str(self.id) + "+" + str(tmp4), "RRP", msg_rec.value)
                        delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()

                elif msg_rec.type == "Message":
                    # check if that is its own
                    tmp2 = msg_rec.nid.split("+")
                    # --------- source ------- prev hop ----- destination ------
                    # update routing table for prev and source node

                    # check
                    if int(tmp2[2]) == self.id: # msg reached dst
                        print("receive " + tmp2[2] + " " + msg_rec.value)

                        global t
                        elapsed = time.time() - t
                        print(elapsed)

                    else:
                        # search in routing table
                        founded = False

                        tmp3 = 0
                        for item2 in self.route_table:
                            if str(item2.key) == tmp2[2]:
                                founded = True
                                tmp3 = item2.nxt_hop
                                break

                        if founded:
                            # relay to next hop
                            # --------- source -------------- next hop ------------ destination ------ current hop
                            m = Message(str(tmp2[0]) + "+" + str(tmp3 ) + "+" + tmp2[2] + "+" + str(self.id), "Message", msg_rec.value)
                            delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                            delayed_send_thread.daemon = True
                            delayed_send_thread.start()

                        else:
                            pass

                elif msg_rec.type == "drop":
                    delayed_send_thread = threading.Thread(target=self.delayed_send, args=([self.recently_sent[0]]))
                    delayed_send_thread.daemon = True
                    delayed_send_thread.start()
                    print("Resend")

    def hello(self):

        m = Message(str(self.id), "hello", str(self.x) + " " + str(self.y))
        delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
        delayed_send_thread.daemon = True
        delayed_send_thread.start()

        global t
        if self.id == 1:
            t = time.time()

    def send_msg(self, msg, dst):

        # Search in routing table
        founded = False
        dst = dst + 1
        tmp4 = 0
        for item5 in self.route_table:
            if str(item5.key) == str(dst):
                founded = True
                tmp4 = item5.nxt_hop
                break

        if founded:
            # relay to next hop
            # --------- source -------------- next hop ------------ destination ------ current hop
            m = Message( str(self.id) + "+" + str(tmp4) + "+" + str(dst) + "+" + str(self.id) , "Message" , msg )
            print("send " + str(self.id) + " " + str(msg))
            delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
            delayed_send_thread.daemon = True
            delayed_send_thread.start()

        else:
            # rrq and then send message
            # --------- current hop -------------- source
            m = Message(str(self.id) + "+" + str(self.id), "RRQ", str(dst) + "+" + str(self.rrq_counter))
            self.rrq_received.append([str(self.id), str(dst), str(self.rrq_counter)])
            self.rrq_counter = self.rrq_counter + 1
            delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
            delayed_send_thread.daemon = True
            delayed_send_thread.start()


            # save message to send later
            delayed_send_thread = threading.Thread(target=self.send_msg_check, args=(msg, dst))
            delayed_send_thread.daemon = True
            delayed_send_thread.start()

    def send_msg_check(self, msg, dst):
        while True:

            time.sleep(0.2)

            founded = False
            nxthop = 0
            for ii, item3  in enumerate(self.route_table):
                if int(item3.key) == int(dst):
                    founded = True
                    nxthop = item3.nxt_hop

            if founded:
                m = Message(str(self.id) + "+" + str(nxthop) + "+" + str(dst) + "+" + str(self.id), "Message", msg)
                print("send " + str(self.id) + " " + str(msg))
                delayed_send_thread = threading.Thread(target=self.delayed_send, args=([m]))
                delayed_send_thread.daemon = True
                delayed_send_thread.start()
                return
            else:
                continue

    def change_loc(self, _x, _y):
        self.x = _x
        self.y = _y

        self.route_table = []
        self.init_finish = False
        self.nbrs = []
        self.rrq_received = []
        self.rrq_counter = 1

        hello_thread = threading.Thread(target=self.hello, args=())
        hello_thread.daemon = True
        hello_thread.start()

# -------------------------------------------------------------------------------------------------------------------
class Server:
    def __init__(self, _n, _ip, _port, _d, _nodes):
        self.ip = _ip
        self.port = _port
        self.d = _d
        self.nodes = _nodes
        self.send_thread = []
        self.n = _n

        self.hello_counter = 0
        self.hello_sent_counter = 0
        self.hello_ack = 0

        main_thread = threading.Thread(target=self.main, args=())
        main_thread.daemon = True
        main_thread.start()

    def main(self):
        server_thread = threading.Thread(target=self.server_up, args=())
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1 * self.n)
        connect_thread = threading.Thread(target=self.connect, args=())
        connect_thread.daemon = True
        connect_thread.start()

    def server_up(self):
        server_socket = socket.socket()
        server_socket.bind((self.ip, self.port))
        while True:
            server_socket.listen(2)
            conn, address = server_socket.accept()
            listen_thread = threading.Thread(target=self.listen, args=([conn]))
            listen_thread.daemon = True
            listen_thread.start()

    def connect(self):
        for ii in range(len(self.nodes)):
            client_socket = socket.socket()
            client_socket.connect((self.nodes[ii][1], self.nodes[ii][2])) # ------------------------- order is imp
            self.send_thread.append(client_socket)

    def listen(self, conn):
        while True:
            data = conn.recv(1024)
            if not data:
                break
            else:
                prob_drop = random.uniform(0, 1)

                msg_rec = Message(**json.loads(data, encoding="utf-8"))

                if msg_rec.type == "hello":
                    tmp_id = int(msg_rec.nid) - 1

                    if prob_drop > p:
                        m = Message(" ", "drop", " ")
                        delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp_id), [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()
                        print("Drop")
                        continue

                    self.hello_counter = self.hello_counter + 1
                    tmp_id = int(msg_rec.nid) - 1
                    tmp_loc = [int(item3) for item3 in msg_rec.value.split()]
                    self.nodes[tmp_id][3] = tmp_loc[0]
                    self.nodes[tmp_id][4] = tmp_loc[1]

                    if self.hello_counter == n:
                        self.hello_all()
                        self.hello_counter = 0

                elif msg_rec.type == "hello_ack":

                    if prob_drop > p:
                        m = Message(" ", "drop", " ")
                        delayed_send_thread = threading.Thread(target=self.send_single, args=(int(msg_rec.nid) - 1, [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()
                        print("Drop")
                        continue

                    nbr_list = [int(msg_rec.value)]
                    delayed_send_thread = threading.Thread(target=self.send_nbrs, args=(nbr_list, [msg_rec]))
                    delayed_send_thread.daemon = True
                    delayed_send_thread.start()
                    self.hello_ack = self.hello_ack + 1
                    if self.hello_ack == self.hello_sent_counter:
                        m = Message(str(self.n * self.n), "init_finish", "none")
                        self.send_to_all([m])
                        self.hello_sent_counter = 0
                        self.hello_ack = 0

                elif msg_rec.type == "RRQ":
                    tmp2 = msg_rec.nid.split("+")
                    if prob_drop > p:
                        m = Message(" ", "drop", " ")
                        delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp2[0]) - 1, [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()
                        print("Drop")
                        continue

                    # --------- source -------------- prev hop
                    nbr_list = self.get_nbrs(int(tmp2[0]) - 1)
                    if nbr_list:
                        m = Message(msg_rec.nid, "RRQ", msg_rec.value)
                        delayed_send_thread = threading.Thread(target=self.send_nbrs, args=(nbr_list, [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()

                elif msg_rec.type == "RRP":

                    tmp3 = msg_rec.nid.split("+")

                    if prob_drop > p:
                        m = Message(" ", "drop", " ")
                        delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp3[0]) - 1, [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()
                        print("Drop")
                        continue

                    m = Message(tmp3[0], "RRP", msg_rec.value)
                    delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp3[1]), [m]))
                    delayed_send_thread.daemon = True
                    delayed_send_thread.start()

                elif msg_rec.type == "Message":
                    # --------- source -------------- next hop ------------ destination ------ prev hop
                    tmp2 = msg_rec.nid.split("+")
                    if prob_drop > p:
                        m = Message(" ", "drop", " ")
                        delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp2[3]) - 1, [m]))
                        delayed_send_thread.daemon = True
                        delayed_send_thread.start()
                        print("Drop")
                        continue


                    m = Message(tmp2[0] + "+" + tmp2[3] + "+" + tmp2[2], "Message", msg_rec.value)
                    delayed_send_thread = threading.Thread(target=self.send_single, args=(int(tmp2[1]), [m]))
                    delayed_send_thread.daemon = True
                    delayed_send_thread.start()

    def hello_all(self):
        for iii in range(n):
            nbr_list = self.get_nbrs(iii)

            if nbr_list:
                m = Message(str(iii + 1), "hello", str(self.nodes[iii][3]) + " " + str(self.nodes[iii][4]))
                delayed_send_thread = threading.Thread(target=self.send_nbrs, args=(nbr_list, [m]))
                delayed_send_thread.daemon = True
                delayed_send_thread.start()
                self.hello_sent_counter = self.hello_sent_counter + len(nbr_list)

    def send_to_all(self, msg):
        byte_array = json.dumps(msg[0].__dict__).encode("utf-8")
        for item3 in self.send_thread:
            time.sleep(random.uniform(0, 1))
            item3.send(byte_array)

    def send_single(self, dst, msg):
        byte_array = json.dumps(msg[0].__dict__).encode("utf-8")
        time.sleep(random.uniform(0, 1))
        self.send_thread[dst - 1].send(byte_array)

    def send_nbrs(self, nbr_list, msg):
        byte_array = json.dumps(msg[0].__dict__).encode("utf-8")
        for item3 in nbr_list:
            time.sleep(random.uniform(0, 1))
            self.send_thread[item3 - 1].send(byte_array)

    def get_nbrs(self, xx):
        nbr_list = []
        for item3 in self.nodes:
                if item3[0] != self.nodes[xx][0]:
                    if  (item3[3] - self.nodes[xx][3] ) * (item3[3] - self.nodes[xx][3] ) + (item3[4] - self.nodes[xx][4]) * (item3[4] - self.nodes[xx][4])  < self.d * self.d:
                        nbr_list.append(item3[0])
        return nbr_list

# Main ------------------------------------------------------------------------------
# input
d = int(input())
x = int(input())
y = int(input())
n = int(input())

node_data = []
for i in range(n):
    tmp = input().split()
    node_data.append(tmp)

g = BattleGround(x, y)
server_ip = "127.0.0.1"
server_port = 6000

nodes = []
# Node Constructor
for i in range(n):
    tmp = node_data[i]
    nodes.append(Vehicle(int(tmp[0]), int(tmp[3]), int(tmp[4]), tmp[1], int(tmp[2]), int(tmp[5]), server_ip, server_port ,g, n))

# Prepare data foe server
node_data = []
for i in range(n):
    node_data.append([nodes[i].id, nodes[i].ip, nodes[i].port, 0, 0])
server = Server(n, server_ip, server_port, d, node_data)

# wait until first step is finished
while True:
    tmp = True
    for item in nodes:
        tmp = item.init_finish and tmp
    if tmp:
        print("Initialization has been finished successfully")
        break

f = open("scenario.txt", "r")
f1 = f.readlines()
commands = []
for x in f1:
    commands.append(x)

for item in commands:
    tmp = item.split(" ")

    if tmp[0] == "SendMessage":
        info = tmp[1].split("-")
        nodes[int(info[0]) - 1].send_msg(info[1], int(info[2]) - 1)

    elif tmp[0] == "ChangeLoc":
        print("change location")
        # do the work
        tmp3 = ""
        for item3 in tmp[1:]:
            tmp2 = item3.split("-")
            if int(tmp2[1]) > g.x or int(tmp2[2]) > g.y:
                print("location error")
            else:
                tmp3 = tmp3 + str(tmp2[0]) + "(" + str(tmp2[1]) + "," + str(tmp2[2]) + ")" + "-"
        print(tmp3)

        for item2 in tmp[1:]:
            tmp2 = item2.split("-")
            nodes[int(tmp2[0]) - 1].change_loc(int(tmp2[1]), int(tmp2[2]))

        # wait to finish the job
        while True:
            tmp = True
            for item2 in nodes:
                tmp = item2.init_finish and tmp
            if tmp:
                print("New neighbors has been founded successfully")
                break

    elif tmp[0] == "Wait":
        print("Waiting ............... ")
        time.sleep(int(tmp[1]))

time.sleep(n * n * n)
