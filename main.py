from PBFT import *
from client import *

import threading
import time

# Parameters to be defined by the user

waiting_time_before_resending_request = 200  # Time the client will wait before resending the request. This time, it broadcasts the request to all nodes
timer_limit_before_view_change = 120  # There is no value proposed in the paper so let's fix it to 120s
checkpoint_frequency = 100  # 100 is the proposed value in the original article


def type_node():
    while True:
        ecc.define_type_of_node(type_nodes)
        global num_node
        num_node = input()
        if num_node in type_nodes:
            num_node = int(num_node)
            prepare()
            break
        else:
            print("Sth wrong")
        return num_node


def prepare():
    ecc.save_file('messages_formats/type_format.json', {})


type_nodes = {
    '1': 'faulty_primary',
    '2': 'slow_nodes',
    '3': 'honest_node',
    '4': 'non_responding_node',
    '5': 'faulty_node',
    '6': 'faulty_replies_node',

}

nodes = {
    0: [
        ("faulty_primary", 0),
        ("slow_nodes", 0),
        ("honest_node", 10),
        ("non_responding_node", 0),
        ("faulty_node", 0),
        ("faulty_replies_node", 0),
    ]
}

# Running PBFT protocol
run_PBFT(nodes=nodes, proportion=1, checkpoint_frequency0=checkpoint_frequency, clients_ports0=clients_ports,
         timer_limit_before_view_change0=timer_limit_before_view_change)

time.sleep(1)  # Waiting for the network to start...

# Run clients:
requests_number = 10
# The user chooses the number of requests he wants to execute simultaneously
# (They are all sent to the PBFT network at the same time) - Here each request will be sent by a different client
clients_list = []
for i in range(requests_number):
    globals()["C%s" % str(i)] = Client(i, waiting_time_before_resending_request)
    clients_list.append(globals()["C%s" % str(i)])
for i in range(requests_number):
    threading.Thread(target=clients_list[i].send_to_primary,
                     args=("Requester  " + str(i), get_primary_id(), get_nodes_ids_list(), get_f())).start()
    time.sleep(0)
