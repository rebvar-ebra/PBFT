# 📜 Practical Byzantine Fault Tolerance (PBFT)

This repository contains an implementation of the classic **Practical Byzantine Fault Tolerance (PBFT)** protocol, a robust consensus algorithm designed to maintain reliability and integrity even in the presence of faulty or malicious nodes.

## 🤔 Why Use PBFT?

PBFT (Practical Byzantine Fault Tolerance) is highly recommended for networks where a level of trust exists among participants, such as enterprise consortiums or permissioned blockchains. Its key advantages are:

- **Resilience to Byzantine Faults**: Handles both crash faults and arbitrary (malicious) behavior.
- **Finality**: Decisions are finalized without the need for probabilistic confirmations, unlike Proof-of-Work algorithms.
- **Reduced Latency**: Designed to work efficiently in partially trusted environments.

> **Use Case**: PBFT is a great choice for enterprise environments where members are known but not entirely trusted, such as financial networks or consortium blockchains.

## 🚫 Drawbacks of PBFT

The major drawback of PBFT is its high message complexity. As more nodes (replicas) are added to the network, the number of messages exchanged grows exponentially, leading to scalability issues.

### 📈 Why So Many Messages?

PBFT’s message overhead is due to its **three-phase protocol** (pre-prepare, prepare, and commit), where each replica needs to communicate with every other replica at least once in every phase. This message-heavy process ensures that all non-faulty nodes can reach a consensus even if a subset is malicious.

### 🔢 Why So Many Replicas?

In PBFT, the number of replicas \( |R| \) is determined by the formula:

\[
|R| = 3f + 1
\]

where:
- \( f \) is the maximum number of faulty nodes (both malicious and crashed).
- The minimum number of replicas is set to ensure that non-faulty nodes can always outvote faulty ones.

For example:
- If \( f = 2 \), then \( |R| = 3(2) + 1 = 7 \).
  - This means, with 7 replicas, PBFT can tolerate up to 2 faulty replicas.

## 🧮 Example Replica Set

If we want a network that can tolerate **up to 2 faulty replicas**, the minimum replica set would be 7 nodes. The nodes would consist of:

- 1 Primary node
- 6 Backup replicas

Thus, we can tolerate 2 faulty replicas while maintaining consensus. The relationship between nodes and messages is outlined in the next section.

## 💌 Total Message Count Per Client Request

The total number of messages exchanged in PBFT depends on the number of replicas and the different phases of the algorithm. Here’s a breakdown for a typical request-response cycle:

### 📜 Formula for Calculating Messages

Given the formula for message calculation, we have:

\[
\text{Total messages} = 1 + 3f + 3f(3f-f) + (3f-f+1)(3f+1) + 3f-1
\]

Where each term represents:

- **Request messages**: \( 1 \)
- **Pre-prepare messages**: \( 3f \)
- **Prepare messages**: \( 3f(3f-f) \)
- **Commit messages**: \( (3f-f+1)(3f+1) \)
- **Reply messages**: \( 3f-1 \)

For a replica set with \( f = 2 \) faulty nodes, we get:

- Request messages: 1
- Pre-prepare messages: 6
- Prepare messages: 24
- Commit messages: 35
- Reply messages: 5

**Total Messages**: \( 1 + 6 + 24 + 35 + 5 = 71 \)

If we increase the number of faulty nodes to 3, the message count jumps to 142, and for 4 faulty nodes, it skyrockets to 237!

> **Conclusion**: PBFT’s high message overhead makes it unsuitable for large-scale, public networks but remains highly effective for smaller, controlled networks with partially trusted nodes.

## ⚡ Optimizations for PBFT

While we can’t reduce the number of messages exchanged, we can optimize the **cryptographic verification** used in PBFT messages. Instead of using computationally heavy **RSA digital signatures**, we can use **MACs (Message Authentication Codes)**, such as **SHA-256**, for faster message authentication.

### 🔐 Why Use MACs?

- **Lower Computational Cost**: MACs are significantly faster to compute compared to RSA digital signatures.
- **Selective Use of RSA**: RSA digital signatures are only used during **view changes** (when the primary is replaced), reducing overhead during normal operation.

### 🔎 Research Insight

In the original 1999 PBFT paper by **Miguel Castro and Barbara Liskov** from MIT, it was found that MACs are **three orders of magnitude** faster than RSA digital signatures. Although their comparison was between MD5 and 1024-bit RSA, the principle still holds true for modern algorithms like SHA-256 and 2048-bit RSA.

## 🏁 Conclusion

PBFT is often misunderstood as an unscalable consensus algorithm. However, this view stems from a misconception that **node == server**, which is not the case in practical deployments. In real-world applications:

- **Node == Organization**: Each node represents a consortium member (an entire organization, not a single server).
- **Clustered Nodes**: Each organization can scale internally using clusters of servers behind a single node.

By structuring nodes in this manner, PBFT can provide high throughput and reliability in **enterprise environments** where trust is partial, and fault tolerance is a necessity.

## 📚 References

- **Original Paper**: Miguel Castro and Barbara Liskov. "Practical Byzantine Fault Tolerance." *Proceedings of the Third Symposium on Operating Systems Design and Implementation (OSDI)*, 1999.
- **Further Reading**: [PBFT on Wikipedia](https://en.wikipedia.org/wiki/Practical_Byzantine_Fault_Tolerance)
