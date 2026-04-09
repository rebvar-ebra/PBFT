import threading
from threading import Lock
import socket
import json
import time
import hashlib
import ecc
import argparse
import sys
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
import output

# --- Constants & Templates ---

class MessageTemplates:
    @staticmethod
    def get(msg_type, **kwargs):
        templates = {
            "REQUEST": {
                "message_type": "REQUEST",
                "request": "",
                "timestamp": 0,
                "client_id": 0
            },
            "PREPREPARE": {
                "message_type": "PREPREPARE",
                "view_number": 0,
                "sequence_number": 0,
                "request_digest": "",
                "request": "",
                "timestamp": 0,
                "client_id": 0,
                "node_id": 0
            },
            "PREPARE": {
                "message_type": "PREPARE",
                "view_number": 0,
                "sequence_number": 0,
                "request_digest": "",
                "request": "",
                "node_id": 0,
                "client_id": 0,
                "timestamp": 0
            },
            "COMMIT": {
                "message_type": "COMMIT",
                "view_number": 0,
                "sequence_number": 0,
                "node_id": 0,
                "client_id": 0,
                "request_digest": "",
                "request": "",
                "timestamp": 0
            },
            "REPLY": {
                "message_type": "REPLY",
                "view_number": 0,
                "client_id": 0,
                "node_id": 0,
                "timestamp": 0,
                "result": "",
                "sequence_number": 0,
                "request": "",
                "request_digest": ""
            },
            "CHECKPOINT": {
                "message_type": "CHECKPOINT",
                "sequence_number": 0,
                "checkpoint_digest": "",
                "node_id": 0
            },
            "VOTE": {
                "message_type": "VOTE",
                "sequence_number": 0,
                "checkpoint_digest": "",
                "node_id": 0
            },
            "VIEW-CHANGE": {
                "message_type": "VIEW-CHANGE",
                "new_view": 0,
                "last_sequence_number": 0,
                "C": [],
                "P": [],
                "node_id": 0
            },
            "NEW-VIEW": {
                "message_type": "NEW-VIEW",
                "new_view_number": 0,
                "V": [],
                "O": []
            }
        }
        res = templates.get(msg_type, {}).copy()
        res.update(kwargs)
        return res

# --- Global Configurations (Loaded once) ---

ports_file = "ports.json"
try:
    with open(ports_file) as f:
        ports_data = json.load(f)
    NODES_PORTS = [(ports_data["nodes_starting_port"] + i) for i in range(ports_data["nodes_max_number"])]
    CLIENTS_PORTS = [(ports_data["clients_starting_port"] + i) for i in range(ports_data["clients_max_number"])]
except Exception as e:
    output.log_error_loading_ports(e)
    sys.exit(1)

def recv_all(sock):
    data = b""
    sock.settimeout(5.0)
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk: break
            data += chunk
        except: break
    return data

# --- Network Manager ---

class PBFTNetwork:
    """Manages the cluster of nodes and collection of metrics."""
    def __init__(self, checkpoint_frequency=100, view_timeout=120):
        self.nodes = []
        self.node_ids = []
        self.checkpoint_frequency = checkpoint_frequency
        self.view_timeout = view_timeout
        
        # Metrics
        self.total_processed_messages = 0
        self.processed_requests = 0
        self.first_reply_time = None
        self.replied_requests = {} # {request_text: 1/0}
        self.accepted_replies = {} # {request_text: result}
        self.request_message_counts = {} # {request_text: count}
        self.clients_last_request_time = {} # {client_id: timestamp}
        
        self.lock = Lock()
        self.sequence_number = 1
        self.f = 0

    def add_node(self, node):
        with self.lock:
            self.nodes.append(node)
            self.node_ids.append(node.node_id)
            self.f = (len(self.nodes) - 1) // 3

    def increment_message_count(self, request_text):
        with self.lock:
            self.total_processed_messages += 1
            self.request_message_counts[request_text] = self.request_message_counts.get(request_text, 0) + 1

    def mark_request_replied(self, request_text, result):
        with self.lock:
            if request_text not in self.replied_requests:
                self.processed_requests += 1
                if self.processed_requests == 1:
                    self.first_reply_time = time.time()
                
                self.replied_requests[request_text] = 1
                self.accepted_replies[request_text] = result
                
                if self.processed_requests % 5 == 0:
                    delta = time.time() - self.first_reply_time
                    output.log_network_validation(self.processed_requests, delta)
            
            return self.request_message_counts.get(request_text, 0)

    def get_primary_id(self, view_number):
        if not self.node_ids: return 0
        return self.node_ids[view_number % len(self.node_ids)]

# --- Node Implementation ---

class Node:
    def __init__(self, node_id, network):
        self.node_id = node_id
        self.network = network
        self.port = NODES_PORTS[node_id]
        
        # State
        self.view_number = 0
        self.primary_node_id = 0
        self.sequence_number = 1
        
        # Logs
        self.message_log = []
        self.preprepares = {} # (view, seq) -> digest
        self.prepares = {}    # (view, seq, digest) -> set(node_ids)
        self.commits = {}     # (view, seq, digest) -> count
        self.replies = {}     # client_id -> [last_msg, last_reply]
        self.last_reply_timestamp = {} # client_id -> timestamp
        
        # Checkpoints
        self.checkpoints = {} # (seq, digest) -> set(node_ids)
        self.checkpoints_seq_seen = set()
        self.stable_checkpoint = {"sequence_number": 0, "digest": "init"}
        self.h = 0 # Low watermark
        self.H = 200 # High watermark
        
        # View Change
        self.accepted_requests_time = {} # request -> start_time
        self.received_view_changes = {} # new_view -> [messages]
        self.asked_view_change = set()
        
        # Networking
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((socket.gethostname(), self.port))
        self.socket.listen(10)

    def receive_loop(self, waiting_time=0):
        while True:
            try:
                c, _ = self.socket.accept()
                raw_data = recv_all(c)
                c.close()
                if not raw_data: continue

                # Strip signature
                [signed_msg, pub_key_raw] = raw_data.split(b'split')
                verify_key = VerifyKey(pub_key_raw)
                decoded_msg = verify_key.verify(signed_msg).decode().replace("'", '"')
                message = json.loads(decoded_msg)
                
                threading.Thread(target=self.process_message, args=(message, waiting_time), daemon=True).start()
            except Exception:
                pass

    def process_message(self, msg, waiting_time):
        # 1. Check for view change triggers
        self.check_view_timeout()
        
        m_type = msg.get("message_type")
        
        # 2. Filter messages based on view (except view change related)
        if m_type not in ["CHECKPOINT", "VOTE", "VIEW-CHANGE", "NEW-VIEW"]:
            if msg.get("view_number") is not None and msg["view_number"] != self.view_number:
                if m_type != "REQUEST": return
        
        # 3. Route to handlers
        handlers = {
            "REQUEST": self.handle_request,
            "PREPREPARE": self.handle_preprepare,
            "PREPARE": self.handle_prepare,
            "COMMIT": self.handle_commit,
            "CHECKPOINT": self.handle_checkpoint,
            "VOTE": self.handle_vote,
            "VIEW-CHANGE": self.handle_view_change,
            "NEW-VIEW": self.handle_new_view
        }
        
        handler = handlers.get(m_type)
        if handler:
            if waiting_time > 0: time.sleep(waiting_time)
            handler(msg)

    # --- Handlers ---

    def handle_request(self, msg):
        req_text = msg["request"]
        client_id = msg["client_id"]
        ts = msg["timestamp"]
        
        if req_text not in self.network.replied_requests:
            self.network.replied_requests[req_text] = 0
            
        if req_text not in self.accepted_requests_time:
            self.accepted_requests_time[req_text] = time.time()
            
        # If I'm the primary, start consensus
        if self.node_id == self.network.get_primary_id(self.view_number):
            last_ts = self.network.clients_last_request_time.get(client_id, 0)
            if ts > last_ts:
                self.network.clients_last_request_time[client_id] = ts
                self.broadcast_preprepare(msg)
        else:
            # Forward to primary
            self.send_to_node(self.network.get_primary_id(self.view_number), msg)

    def handle_preprepare(self, msg):
        self.network.increment_message_count(msg["request"])
        digest = hashlib.sha256(msg["request"].encode()).hexdigest()
        
        if digest == msg["request_digest"] and msg["view_number"] == self.view_number:
            key = (msg["view_number"], msg["sequence_number"])
            if key not in self.preprepares:
                self.preprepares[key] = digest
                self.message_log.append(msg)
                self.broadcast_prepare(msg)

    def handle_prepare(self, msg):
        self.network.increment_message_count(msg["request"])
        key = (msg["view_number"], msg["sequence_number"], msg["request_digest"])
        
        if key not in self.prepares: self.prepares[key] = set()
        self.prepares[key].add(msg["node_id"])
        
        # Check if prepared
        is_preprepared = any(m["message_type"] == "PREPREPARE" and m["sequence_number"] == msg["sequence_number"] for m in self.message_log)
        if is_preprepared and len(self.prepares[key]) >= (2 * self.network.f):
            self.broadcast_commit(msg)

    def handle_commit(self, msg):
        self.network.increment_message_count(msg["request"])
        key = (msg["view_number"], msg["sequence_number"], msg["request_digest"])
        
        self.commits[key] = self.commits.get(key, 0) + 1
        
        if self.commits[key] >= (2 * self.network.f + 1) and key in self.prepares:
            # Execute and reply
            if self.last_reply_timestamp.get(msg["client_id"], 0) < msg["timestamp"]:
                result = self.execute_request(msg)
                self.send_reply(msg, result)
                
                # Checkpointing
                if msg["sequence_number"] % self.network.checkpoint_frequency == 0:
                    self.create_checkpoint(msg, result)

    def handle_checkpoint(self, msg):
        # Verify checkpoint and vote
        for m in self.network.nodes[self.node_id].message_log: # Simple logic: vote if we have the reply
            if m["message_type"] == "REPLY" and m["sequence_number"] == msg["sequence_number"]:
                # (Simulated verification)
                vote = MessageTemplates.get("VOTE", sequence_number=msg["sequence_number"], 
                                          checkpoint_digest=msg["checkpoint_digest"], node_id=self.node_id)
                self.send_to_node(msg["node_id"], ecc.generate_sign(vote))

    def handle_vote(self, msg):
        key = (msg["sequence_number"], msg["checkpoint_digest"])
        if key not in self.checkpoints: self.checkpoints[key] = set()
        self.checkpoints[key].add(msg["node_id"])
        
        if len(self.checkpoints[key]) >= (2 * self.network.f + 1):
            self.stable_checkpoint = {"sequence_number": msg["sequence_number"], "digest": msg["checkpoint_digest"]}
            self.h = msg["sequence_number"]
            # Clear old logs... (optional in simulation)

    def handle_view_change(self, msg):
        new_v = msg["new_view"]
        if self.network.get_primary_id(new_v) == self.node_id:
            if new_v not in self.received_view_changes: self.received_view_changes[new_v] = []
            self.received_view_changes[new_v].append(msg)
            
            if len(self.received_view_changes[new_v]) >= (2 * self.network.f):
                self.broadcast_new_view(new_v)

    def handle_new_view(self, msg):
        self.view_number = msg["new_view_number"]
        self.primary_node_id = self.network.get_primary_id(self.view_number)
        self.asked_view_change.clear()
        output.log_node_view_entry(self.node_id, self.view_number)

    # --- Actions ---

    def broadcast_preprepare(self, req_msg):
        with self.network.lock:
            seq = self.network.sequence_number
            self.network.sequence_number += 1
            
        digest = hashlib.sha256(req_msg["request"].encode()).hexdigest()
        msg = MessageTemplates.get("PREPREPARE", 
            view_number=self.view_number, sequence_number=seq,
            request_digest=digest, request=req_msg["request"],
            timestamp=req_msg["timestamp"], client_id=req_msg["client_id"], node_id=self.node_id
        )
        self.preprepares[(self.view_number, seq)] = digest
        self.message_log.append(msg)
        self.broadcast(ecc.generate_sign(msg))

    def broadcast_prepare(self, preprepare_msg):
        msg = MessageTemplates.get("PREPARE",
            view_number=self.view_number, sequence_number=preprepare_msg["sequence_number"],
            request_digest=preprepare_msg["request_digest"], request=preprepare_msg["request"],
            node_id=self.node_id, client_id=preprepare_msg["client_id"], timestamp=preprepare_msg["timestamp"]
        )
        self.broadcast(ecc.generate_sign(msg))

    def broadcast_commit(self, prepare_msg):
        msg = MessageTemplates.get("COMMIT",
            view_number=self.view_number, sequence_number=prepare_msg["sequence_number"],
            node_id=self.node_id, client_id=prepare_msg["client_id"],
            request_digest=prepare_msg["request_digest"], request=prepare_msg["request"],
            timestamp=prepare_msg["timestamp"]
        )
        self.broadcast(ecc.generate_sign(msg))

    def send_reply(self, commit_msg, result):
        reply = MessageTemplates.get("REPLY",
            view_number=self.view_number, client_id=commit_msg["client_id"],
            node_id=self.node_id, timestamp=commit_msg["timestamp"],
            result=result, sequence_number=commit_msg["sequence_number"],
            request=commit_msg["request"], request_digest=commit_msg["request_digest"]
        )
        self.last_reply_timestamp[commit_msg["client_id"]] = commit_msg["timestamp"]
        client_port = CLIENTS_PORTS[commit_msg["client_id"]]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((socket.gethostname(), client_port))
            s.send(ecc.generate_sign(reply))
            s.close()
        except: pass

    def execute_request(self, msg):
        # Simulated execution
        self.network.mark_request_replied(msg["request"], "Executed")
        return "Executed"

    def create_checkpoint(self, msg, result):
        digest = hashlib.sha256(str([msg["request_digest"], msg["client_id"], result]).encode()).hexdigest()
        cp = MessageTemplates.get("CHECKPOINT", sequence_number=msg["sequence_number"], 
                                 checkpoint_digest=digest, node_id=self.node_id)
        self.broadcast(ecc.generate_sign(cp))

    def broadcast_new_view(self, new_v):
        msg = MessageTemplates.get("NEW-VIEW", new_view_number=new_v, V=self.received_view_changes[new_v], O=[])
        # (O set construction omitted for brevity, keeping simulation simple)
        self.broadcast(ecc.generate_sign(msg))

    def check_view_timeout(self):
        for req, start_time in list(self.accepted_requests_time.items()):
            if start_time != -1 and (time.time() - start_time) > self.network.view_timeout:
                if self.view_number + 1 not in self.asked_view_change:
                    self.initiate_view_change()
                    break

    def initiate_view_change(self):
        new_v = self.view_number + 1
        self.asked_view_change.add(new_v)
        msg = MessageTemplates.get("VIEW-CHANGE", new_view=new_v, 
                                 last_sequence_number=self.stable_checkpoint["sequence_number"],
                                 node_id=self.node_id)
        self.broadcast(ecc.generate_sign(msg))

    # --- Networking Helpers ---

    def send_to_node(self, target_id, data):
        try:
            target_port = NODES_PORTS[target_id]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((socket.gethostname(), target_port))
            s.send(data)
            s.close()
        except: pass

    def broadcast(self, data):
        for nid in self.network.node_ids:
            if nid != self.node_id:
                self.send_to_node(nid, data)

# --- Specialized Nodes ---

class HonestNode(Node):
    pass

class SlowNode(Node):
    def receive_loop(self):
        super().receive_loop(waiting_time=2.0) # 2 seconds delay

class NonRespondingNode(Node):
    def receive_loop(self):
        while True:
            try:
                c, _ = self.socket.accept()
                recv_all(c) # Just drain
                c.close()
            except: pass

class FaultyPrimary(Node):
    def broadcast_preprepare(self, req_msg):
        # Corrupt the digest
        req_msg_corrupt = req_msg.copy()
        req_msg_corrupt["request"] += " corrupted"
        super().broadcast_preprepare(req_msg_corrupt)

class FaultyNode(Node):
    def broadcast_prepare(self, preprepare_msg):
        # Corrupt the digest in prepare
        corrupt_msg = preprepare_msg.copy()
        corrupt_msg["request_digest"] += "_bad"
        super().broadcast_prepare(corrupt_msg)

class FaultyRepliesNode(Node):
    def execute_request(self, msg):
        return "Faulty Result"

# --- Main Entry Interface ---

_current_network = None

def run_PBFT(nodes, proportion, checkpoint_frequency0, clients_ports0, timer_limit_before_view_change0):
    """Bridge for main.py."""
    network = PBFTNetwork(checkpoint_frequency0, timer_limit_before_view_change0)
    
    def start_nodes():
        node_id_counter = 0
        # nodes is {delay: [(type, count), ...]}
        for delay, types in nodes.items():
            if delay > 0: time.sleep(delay)
            for n_type, count in types:
                for _ in range(count):
                    cls = {
                        "honest_node": HonestNode,
                        "slow_nodes": SlowNode,
                        "non_responding_node": NonRespondingNode,
                        "faulty_primary": FaultyPrimary,
                        "faulty_node": FaultyNode,
                        "faulty_replies_node": FaultyRepliesNode
                    }.get(n_type, HonestNode)
                    
                    node = cls(node_id_counter, network)
                    network.add_node(node)
                    threading.Thread(target=node.receive_loop, daemon=True).start()
                    node_id_counter += 1
        
        # Globally accessible info for main.py compatibility
        global _current_network
        _current_network = network

    threading.Thread(target=start_nodes, daemon=True).start()

def get_primary_id():
    return _current_network.get_primary_id(_current_network.nodes[0].view_number)

def get_nodes_ids_list():
    return _current_network.node_ids

def get_f():
    return _current_network.f

def reply_received(request, result):
    return _current_network.mark_request_replied(request, result)