import argparse
import threading
import time
import sys
from PBFT import *
from client import *
import output

def interactive_wizard(cfg):
    output.show_wizard_header()
    
    def get_input(prompt, default):
        val = input(f"  > {prompt} (default {default}): ").strip()
        try:
            return type(default)(val) if val else default
        except ValueError:
            output.show_invalid_input_warning(default)
            return default

    cfg.honest = get_input("Number of Honest Nodes", 10)
    cfg.faulty_primary = get_input("Number of Faulty Primary Nodes", 0)
    cfg.slow = get_input("Number of Slow Nodes", 0)
    cfg.non_responding = get_input("Number of Non-Responding Nodes", 0)
    cfg.faulty = get_input("Number of Faulty Nodes (Byzantine)", 0)
    cfg.faulty_replies = get_input("Number of Faulty Replies Nodes", 0)
    
    total_n = cfg.honest + cfg.faulty_primary + cfg.slow + cfg.non_responding + cfg.faulty + cfg.faulty_replies
    f_val = (total_n - 1) // 3
    
    output.show_configuration_summary(total_n, f_val)
    
    cfg.checkpoint = get_input("Checkpoint Frequency", 100)
    cfg.view_timeout = get_input("View Change Timeout (seconds)", 120)
    cfg.client_resend = get_input("Client Resend Timeout (ms)", 200)
    cfg.requests = 0
    
    confirm = input("\nStart simulation with this configuration? (Y/n): ").lower()
    if confirm == 'n':
        output.show_config_cancelled()
        sys.exit(0)
        
    return cfg

def send_requests(count, client_resend, start_index=0):
    if count <= 0:
        return
        
    output.show_initiating_requests(count)
    clients_list = []
    for i in range(start_index, start_index + count):
        client = Client(i, client_resend)
        globals()["C%s" % str(i)] = client
        clients_list.append(client)

    client_threads = []
    for i in range(len(clients_list)):
        t = threading.Thread(
            target=clients_list[i].send_to_primary,
            args=("Requester  " + str(i + start_index), get_primary_id(), get_nodes_ids_list(), get_f())
        )
        t.start()
        client_threads.append(t)

    for t in client_threads:
        t.join()
    output.show_batch_processed()

def runtime_menu(client_resend):
    total_requests_sent = 0
    while True:
        output.show_runtime_menu_header()
        
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            try:
                count = int(input("How many requests to send? ").strip())
                send_requests(count, client_resend, start_index=total_requests_sent)
                total_requests_sent += count
            except ValueError:
                output.show_invalid_choice() # Using show_invalid_choice as a generic invalid input warning here, or I could use show_invalid_input_warning if I had a default
        elif choice == '2':
            output.show_network_status(get_primary_id(), get_nodes_ids_list(), get_f())
        elif choice == '3':
            output.show_exit_message()
            break
        else:
            output.show_invalid_choice()

def main():
    parser = argparse.ArgumentParser(description='Practical Byzantine Fault Tolerance (PBFT) Simulation')

    # CLI arguments
    parser.add_argument('-i', '--interactive', action='store_true', help='Enable interactive step-by-step mode')
    parser.add_argument('--honest', type=int, default=10, help='Number of honest nodes')
    parser.add_argument('--faulty-primary', type=int, default=0, help='Number of faulty primary nodes')
    parser.add_argument('--slow', type=int, default=0, help='Number of slow nodes')
    parser.add_argument('--non-responding', type=int, default=0, help='Number of non-responding nodes')
    parser.add_argument('--faulty', type=int, default=0, help='Number of faulty nodes (Byzantine)')
    parser.add_argument('--faulty-replies', type=int, default=0, help='Number of faulty replies nodes')
    parser.add_argument('--requests', type=int, default=10, help='Number of client requests')
    parser.add_argument('--checkpoint', type=int, default=100, help='Checkpoint frequency')
    parser.add_argument('--view-timeout', type=int, default=120, help='Timer limit before view change (seconds)')
    parser.add_argument('--client-resend', type=int, default=200, help='Client waiting time before resending request (ms)')

    args = parser.parse_args()

    if args.interactive:
        args = interactive_wizard(args)

    # Construct nodes configuration
    nodes_config = {
        0: [
            ("faulty_primary", args.faulty_primary),
            ("slow_nodes", args.slow),
            ("honest_node", args.honest),
            ("non_responding_node", args.non_responding),
            ("faulty_node", args.faulty),
            ("faulty_replies_node", args.faulty_replies),
        ]
    }

    # Running PBFT protocol
    run_PBFT(
        nodes=nodes_config,
        proportion=1,
        checkpoint_frequency0=args.checkpoint,
        clients_ports0=CLIENTS_PORTS,
        timer_limit_before_view_change0=args.view_timeout
    )

    time.sleep(1)  # Waiting for the network to start...

    if args.interactive:
        runtime_menu(args.client_resend)
    else:
        send_requests(args.requests, args.client_resend)
    
    output.show_simulation_finished()

if __name__ == "__main__":
    main()
