# Data Network Simulations

Minimalist simulations of two networks using socket programming in python: Ad hoc On-Demand Distance Vector Routing for mobile network, and peer-to-peer file sharing network.

P.S.: These were Data Network Course Projects. I, as the TA of the course, have designed the second simualtion.

## AODV network
### Explanation
Ad hoc On-Demand Distance Vector (AODV) Routing is a routing protocol for mobile ad hoc networks (MANETs) and other wireless ad hoc networks. It is designed to be self-starting in an environment of mobile nodes, withstanding a variety of network behaviors such as node mobility, link failures and packet losses. 

At each node, AODV maintains a routing table. The routing table entry for a destination contains three essential fields: a next hop node, a sequence number and a hop count. All packets destined to the destination are sent to the next hop node. The sequence number acts as a form of time-stamping, and is a measure of the freshness of a route. The hop count represents the current distance to the destination node. FMI refer to RFC3561 [here](https://tools.ietf.org/html/rfc3561).

Reactive protocols use two different operations to find and maintain routes: the route discovery process operation and the route maintenance operation. When a node requires a route to the destination, it initiates a route discovery process within the network. This process is completed once a route found, or all possible route permutations are examined. Route maintenance is the process of responding to changes in the topology that happens after a route has initially been created. When the link is broken, the nodes in the network try to detect link breaks on the established routes.

### Simulation Notabel Components
- Ground: a rectangle with a given width and length. These specifications will be part of the inputs to your simulation model.
- Vehicles: an object that has a pair of (x, y) which point to the current position of a node within the field and an operational radious that determines its range of communication.
- Communication Server: all communications are going through the server. The server must be capable of transmitting messages considering the distance between the nodes. Each vehicle knows about the address of the server and can only send and receive messages via its link with the server. Note that the server is only a simulator for real word situation so there is no need for it in a real scenario.

### Simulation Conventions
- Initialization: read from the console at the beginning
  - d = diameter of every available module.
  - x = length of the field and y = width of the field.
  - n = number of vehicles.
  - Read n line of data associated with each vehicle. Each line should contain the following information.
    - UID    IP   Port    Location_X     Location_Y    Delay    

- Scenario: input commands which are used to instruct the server how to behave. Sample:
  - ``ChangeLoc UID-x-y UID-x-y UID-x-y  ``
  - ``SendMessage sourceUID-message-destUID ``
  - ``Wait TIME_IN_SECONDS``

## Peer-to-peer File Sharing Network
### Explanation
P2P file sharing allows users to access media files such as books, music, movies, and games using a P2P software program that searches for other connected computers on a P2P network to locate the desired content.

Peer-to-peer file sharing technology has evolved through several design stages from the early networks like Napster, which popularized the technology, to later models like the BitTorrent protocol. FMI refer to [this link](https://en.wikipedia.org/wiki/Peer-to-peer_file_sharing).

Here, we construct a network of multiple nodes that have defferent files. And once a node needs files that the node itself dos not have, it floods a message to find the owner of that file. This procedure is proceeded until the owner is found. During this, a route between these two nodes is established and the nodes use source routing to forward the packets.

### Simulation Notabel Components
- Network Class: establishes a network based on a given topology.
- Node Class: a node in a p2p file-sharing network that maintains a list of its availabe neighbors in the network and possesses several files ready to be shared.
- File: each node have a list of its files that resdie in the same directory where the main code is.
### Simulation Conventions
- Network class constructor args:
  - graph_topology = [[node_ID_1, ip_1, port_1, neighbor_nodes_1, link_delay_1, file_list_1], 
                            [node_ID_2, ip_2, port_2, neighbor_nodes_2, link_delay_2, file_list_2],
                            ...]
    - neighbor_nodes_i = [neighbor_ID_1, neighbor_ID_2, ...] 
    - link_delays_i = [link_1_delay, link_2_delay, ...] 
    - file_list_i = [file_name_1, file_name_2, ...] 
  - ``network = Network(graph_topology)``
- Network Initialization
  - A method of the Network Class to make the connections.
  - ``network.init_network()``
- Request a File
  - A method of the Network Class to command a node with its id to request a file.
  - ``network.file_request(node_id, file_name)``
- Delete_node
  - A method of the Network Class to eliminate a node from the network
  - ``network.delete_node(node_id)``
- Add_node
  - A method of the Network Class to add a node to the network
  - ``network.add_node(node_id, ip, port,  [neighbor_id1, neighbor_id2, ...], [neighbor1_ip, neighbor2_ip, ...], [neighbor1_port, neighbor2_port, ...],  [neighbor1_delay, neighbor2_delay, ...], 
file_list)
``
  - Add_file
    -  A method of the Network Class to add a specific file to a specified node in the network
    - ``network.add_file(node_id, file_name)``
  - Remove_file
    - A method of the Network Class to remove a specific file from a specified node in the network
