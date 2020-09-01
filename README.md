# Data Network Simulations

Minimalist simulations of several networks: Ad hoc On-Demand Distance Vector Routing for mobile network, peer to peer Gnutella network, and mobile network.

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
