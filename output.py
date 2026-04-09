
def log_network_validation(requests_count, duration):
    print(f"Network validated {requests_count} requests within {duration:.4f} seconds")

def log_node_view_entry(node_id, view_number):
    print(f"Node {node_id} entered view {view_number}")

def log_client_message_received(client_id, message):
    print("Client %d received message: %s" % (client_id , message))

def log_client_reply_stats(client_id, duration, message_count):
    print("Client %d got reply within %f seconds. The network exchanged %d messages" % (client_id, duration, message_count))

def log_no_reply_warning():
    print("No received reply")

def log_error_loading_ports(error):
    print(f"Error loading ports.json: {error}")


def show_wizard_header():
    print("\n--- PBFT Simulation Configuration Wizard ---")
    print("Please enter the number of nodes for each category.")

def show_invalid_input_warning(default_val):
    print(f"    Invalid input, using default: {default_val}")

def show_configuration_summary(total_n, f_val):
    print(f"\n[Configuration Summary]")
    print(f"  Total Nodes (n): {total_n}")
    print(f"  Fault Tolerance (f): {f_val} (Network can handle up to {f_val} faulty/Byzantine nodes)")

def show_initiating_requests(count):
    print(f"\n--- Initiating {count} client requests ---")

def show_batch_processed():
    print("Batch of requests processed.")

def show_runtime_menu_header():
    print("\n--- PBFT Simulation Runtime Menu ---")
    print("1. Send batch of requests")
    print("2. Check Network Status")
    print("3. Exit")

def show_network_status(primary_id, nodes_ids, f):
    print(f"\n[Network Status]")
    print(f"Primary Node ID: {primary_id}")
    print(f"Nodes IDS List: {nodes_ids}")
    print(f"Faulty Tolerance (f): {f}")

def show_exit_message():
    print("Exiting simulation...")

def show_invalid_choice():
    print("Invalid choice.")

def show_simulation_finished():
    print("\nSimulation session finished.")

def show_config_cancelled():
    print("Configuration cancelled. Exiting.")
