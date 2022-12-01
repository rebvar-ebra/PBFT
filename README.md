# PBFT
This is an implementation of the classic PBFT protocol.
## Why use pBFT?
pBFT (Practical Byzantine Fault Tolerance) is an excellent consensus algorithm for enterprise consortiums where members are partially trusted.

## Drawbacks
The only drawback to pBFT is the exponentially increasing message count as nodes (replicas technically) are added to the set.
## Why so many messages?
The message heavy algorithm is due to the number of multicast messages needed in each phase of the three phase protocol multiplied by each replica in our set.

## Why so many replicas?
We need a minimum of 3f + 1 replicas where f is the maximum number of faulty replicas. This minimum insures we have enough non-faulty replicas to discover the faulty ones (crashes and Byzantine). Thus, a replica set |R| with the maximum number of replicas that can be faulty is expressed as:|R|=3f + 1

## Example replica set
We will need 7 replicas with one of them being the primary, if we want our replica set to tolerate up to 2 faulty replicas. We get 7 replicas by applying the 2 faulty replicas to our formula: 3(2 faulty replicas) + 1 = 7 replicas

I have calculated the minimum and maximum message count for each phase and placed it at the top of the diagram that I have created below. Included are the client request and reply for clarity, even though they are not actually considered phases in the pBFT algorithm.

## Total message count per client request
The total minimum message count for this replica set is:
1 + 3f + 3f(3f-f) + (3f-f+1)(3f+1) + 3f-1

In our case with a max of 2 faulty replicas, that would be:
- request messages: 1
- pre-prepare messages: 3f = 6
- prepare messages: 3f(3f-f) = 24
- commit messages: (3f-f+1)(3f+1)= 35
- reply messages: 3f-1 = 5

This gives us a minimum of 71 (1+6+24+35+5) total messages for 1 request when using 7 replicas! If we want to have just 1 more replica that can be faulty, this number increases to a minimum of 142 messages for 1 request using 10 replicas.

Want up to 4 nodes to be faulty? Just use 13 replicas, but the minimum messages will climb to 237 for a single request.

This is why pBFT does not scale as well as other consensus algorithms.

Unlike load-balancing your EC2 instances, you should never add more replicas than you absolutely need due to the added messages.


## Optimizations to pBFT
We cannot reduce the number of messages with pBFT, so that leaves us with reducing the required cryptographic proof needed for the messages. MACs are orders of magnitude less CPU intensive than RSA digital signatures

For this reason RSA digital signatures are only used for the view change and new-view messages, which are only sent to promote a backup replica to a primary replica. View changes only happen after a primary has become faulty or k requests have been processed. All other messages are authenticated using MACs like SHA256.

Miguel Castro and Barbara Lisk, authors of the original 1999 pBFT paper from MIT found that MACs could be computed three orders of magnitude faster than digital signatures. Although, they were comparing MD5 vs 1024 bit RSA signature, where we now commonly use SHA256 and 2048 bit RSA.


## Conclusion
pBFT is commonly thought of as an algorithm that does not scale. This perception is usually brought on by the notion of a node == server, which should not be the case with pBFT when deployed in an enterprise production environment.

pBFT should be used with a consortium of enterprise organizations, where each organization would represent a node on the network node == organization. Each of these organizational nodes should then have clusters of instances and load balancers behind the node’s endpoint to scale the computational power and insure a quick response time.