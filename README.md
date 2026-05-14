# 📜 Practical Byzantine Fault Tolerance (PBFT)

This repository contains a complete simulation of the classic **Practical Byzantine Fault Tolerance (PBFT)** consensus protocol, implemented in Python. The simulation supports multiple node behavior types, cryptographic message signing, view-change recovery, and checkpointing — closely following the original 1999 Castro & Liskov paper.

---

## 🤔 Why Use PBFT?

PBFT is highly recommended for networks where a level of trust exists among participants, such as enterprise consortiums or permissioned blockchains. Its key advantages are:

- **Resilience to Byzantine Faults**: Handles both crash faults and arbitrary (malicious) behavior.
- **Finality**: Decisions are finalized without probabilistic confirmations, unlike Proof-of-Work algorithms.
- **Reduced Latency**: Designed to work efficiently in partially trusted environments.

> **Use Case**: PBFT is a great choice for enterprise environments where members are known but not entirely trusted — such as financial networks or consortium blockchains.

---

## 🚫 Drawbacks of PBFT

The major drawback of PBFT is its high message complexity. As more nodes (replicas) are added, the number of messages exchanged grows polynomially, leading to scalability challenges.

### 📈 Why So Many Messages?

PBFT's message overhead is due to its **three-phase protocol** (Pre-Prepare → Prepare → Commit), where each replica needs to communicate with every other replica. This ensures all non-faulty nodes reach consensus even if a subset behaves maliciously.

### 🔢 Replica Count Formula

The minimum number of replicas |R| is determined by:

$$|R| = 3f + 1$$

where **f** is the maximum number of faulty nodes the network must tolerate.

**Example**: For `f = 2`, you need at least **7 replicas** (1 primary + 6 backups) to guarantee consensus.

---

## 💌 Message Complexity

For a network with `f` faulty nodes, the total messages exchanged per client request are:

| Phase        | Messages               |
|--------------|------------------------|
| Request      | 1                      |
| Pre-Prepare  | 3f                     |
| Prepare      | 3f × 2f                |
| Commit       | (2f+1) × (3f+1)        |
| Reply        | 3f                     |

**For f = 2**: `1 + 6 + 24 + 35 + 6 = 72 messages`  
**For f = 3**: the count roughly doubles — illustrating why PBFT is best for small-to-medium controlled networks.

> **Conclusion**: High message overhead makes PBFT unsuitable for large public networks, but highly effective for smaller, controlled environments with partially trusted nodes.

---

## ⚡ Cryptographic Design

All inter-node messages in this implementation are signed using **Ed25519** via the [PyNaCl](https://pynacl.readthedocs.io/) library. Each message is:

1. Signed with a freshly generated `SigningKey` (Ed25519).
2. Transmitted alongside the corresponding `VerifyKey` (public key).
3. Verified by the receiver before processing.

Request and state digests use **SHA-256** hashing for integrity checks.

This approach is consistent with the original paper's recommendation to use fast MACs during normal operation and asymmetric signatures for view-change messages — here, Ed25519 provides a fast, modern alternative to the paper's original 1024-bit RSA.

---

## 🏗 Architecture Overview

```
main.py
  ├── Interactive wizard  (interactive_wizard)
  ├── Runtime menu        (runtime_menu)
  └── run_PBFT()  ──────────────────────────────────────────┐
                                                             ▼
PBFT.py                                              PBFTNetwork
  ├── Node (base class)                                ├── node registry
  │     ├── receive_loop  (TCP server per node)        ├── global sequence number
  │     ├── process_message                            ├── message counters
  │     ├── handle_request / preprepare / prepare      └── checkpoint + reply tracking
  │     ├── handle_commit / checkpoint / vote
  │     ├── handle_view_change / new_view
  │     └── broadcast / send_to_node
  ├── HonestNode
  ├── SlowNode          (2 s processing delay)
  ├── NonRespondingNode (drains socket, never processes)
  ├── FaultyPrimary     (corrupts request payload in Pre-Prepare)
  ├── FaultyNode        (corrupts digest in Prepare)
  └── FaultyRepliesNode (returns wrong result in Reply)

client.py
  └── Client
        ├── send_to_primary  (unicast → primary, wait for f+1 matching replies)
        └── broadcast_request (fallback broadcast on timeout)

ecc.py
  ├── generate_sign(msg)    → Ed25519 signature + public key
  ├── generate_verify(pk, msg) → verified plaintext
  └── hashing_function(x)  → SHA-256 hex digest

output.py
  └── Logging and UI helpers (wizard, menus, status, warnings)
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.8+
- `pip` or `pip3`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> The only runtime dependency is **PyNaCl** (`pynacl`), which provides Ed25519 signing and verification.

### 3. Configure Ports

Open `ports.json` and verify the port ranges are free on your system:

```json
{
  "nodes_starting_port": 3000,
  "nodes_max_number": 50,
  "clients_starting_port": 30000,
  "clients_max_number": 50
}
```

Nodes listen on ports starting at `3000`; clients listen on ports starting at `30000`.

### 4. Run the Simulation

#### One-Shot Mode

Specify all parameters upfront and let the simulation run to completion:

```bash
python3 main.py --honest 7 --faulty 2 --requests 5
```

#### Interactive Mode (Wizard & Menu)

Use the `-i` flag to be guided through configuration and control the simulation step-by-step:

```bash
python3 main.py -i
```

In interactive mode, a configuration wizard collects node counts and timing parameters, then a runtime menu lets you send batches of requests and inspect network status at your own pace.

---

## ⚙️ CLI Reference

| Flag                | Type  | Default | Description                                                  |
|---------------------|-------|---------|--------------------------------------------------------------|
| `-i` / `--interactive` | flag | —    | Enable interactive wizard + runtime menu                    |
| `--honest`          | int   | 10      | Number of honest nodes                                       |
| `--faulty-primary`  | int   | 0       | Faulty primary nodes (corrupt Pre-Prepare payloads)         |
| `--slow`            | int   | 0       | Slow nodes (2 s processing delay)                            |
| `--non-responding`  | int   | 0       | Non-responding nodes (drain socket, send no replies)         |
| `--faulty`          | int   | 0       | Byzantine nodes (corrupt Prepare digest)                     |
| `--faulty-replies`  | int   | 0       | Faulty-reply nodes (return wrong execution result)           |
| `--requests`        | int   | 10      | Number of client requests to send (one-shot mode)            |
| `--checkpoint`      | int   | 100     | Checkpoint frequency (every N committed requests)            |
| `--view-timeout`    | int   | 120     | Seconds before a node triggers a view change                 |
| `--client-resend`   | int   | 200     | Client socket timeout in ms before re-broadcasting a request |

> **Fault safety**: The network tolerates faults as long as the total number of non-honest nodes (`faulty-primary + faulty + faulty-replies + non-responding`) stays within `f = (total_nodes - 1) // 3`.

---

## 🔬 Node Behavior Types

| Type                | Class                | Behavior                                                                 |
|---------------------|----------------------|--------------------------------------------------------------------------|
| Honest              | `HonestNode`         | Follows the PBFT protocol faithfully.                                    |
| Slow                | `SlowNode`           | Introduces a 2-second delay before processing each message.              |
| Non-Responding      | `NonRespondingNode`  | Accepts connections and drains data but never processes or replies.      |
| Faulty Primary      | `FaultyPrimary`      | Broadcasts Pre-Prepare with a corrupted request payload.                 |
| Byzantine           | `FaultyNode`         | Broadcasts Prepare with an invalid digest (`_bad` suffix).               |
| Faulty Replies      | `FaultyRepliesNode`  | Executes requests but returns `"Faulty Result"` instead of `"Executed"`. |

---

## 📁 Project Structure

```
PBFT/
├── PBFT.py               # Core protocol: PBFTNetwork, Node, all node subclasses, message handlers
├── client.py             # Client: sends requests, gathers f+1 matching replies
├── ecc.py                # Cryptographic utilities: Ed25519 signing, SHA-256 hashing
├── main.py               # Entry point: CLI parsing, interactive wizard, runtime menu
├── output.py             # Output helpers: logging, wizard UI, menus, status display
├── ports.json            # Network configuration: node and client port ranges
├── requirements.txt      # Python dependencies (pynacl)
├── test_f_logic.py       # Unit test for fault-tolerance (f) calculation logic
└── messages_formats/     # JSON schemas documenting each PBFT message type
    ├── request_format.json
    ├── preprepare_format.json
    ├── prepare_format.json
    ├── commit_format.json
    ├── reply_format.json
    ├── checkpoint_format.json
    ├── checkpoint_vote_format.json
    ├── view_change_format.json
    └── new_view_format.json
```

---

## 🔄 Protocol Flow

```
Client ──REQUEST──► Primary
                       │
               PREPREPARE (broadcast)
                       │
              ◄──── Backups ────►
               PREPARE (broadcast)
                       │
              ◄──── Backups ────►
               COMMIT (broadcast)
                       │
              REPLY ──► Client
                       │
         (every N commits) CHECKPOINT
```

1. **Request**: Client sends a signed request to the primary node.
2. **Pre-Prepare**: Primary assigns a sequence number, signs, and broadcasts to all replicas.
3. **Prepare**: Each replica verifies the digest and broadcasts a signed Prepare to all peers.
4. **Commit**: Once a replica collects `2f` matching Prepares, it broadcasts a signed Commit.
5. **Reply**: Once `2f+1` matching Commits are received, the replica executes and replies to the client.
6. **Acceptance**: The client accepts the result after receiving `f+1` identical replies.
7. **Checkpoint**: Every `--checkpoint` committed requests, nodes broadcast and collect stable checkpoint proofs, advancing the low watermark `h`.
8. **View Change**: If a request is not completed within `--view-timeout` seconds, nodes broadcast a View-Change. The new primary collects `2f` View-Change messages and broadcasts a New-View.

---

## 🏁 Scalability Note

PBFT is often dismissed as unscalable, but this view conflates **node** with **server**. In real-world deployments:

- **Node = Organization**: Each node represents a consortium member — not a single server.
- **Clustered Nodes**: Each organization can run a cluster of servers internally, presenting a single PBFT node to the network.

This structure lets PBFT provide high throughput and strong fault tolerance for **enterprise environments** where participants are known but not fully trusted.

---

## 📚 References

- **Original Paper**: Miguel Castro and Barbara Liskov. *"Practical Byzantine Fault Tolerance."* Proceedings of OSDI, 1999.
- **PyNaCl Documentation**: <https://pynacl.readthedocs.io/>
- **Further Reading**: [PBFT on Wikipedia](https://en.wikipedia.org/wiki/Practical_Byzantine_Fault_Tolerance)
