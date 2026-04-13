# Redis Atomicity, Race Conditions & Concurrency Notes

## 🧠 Core Concepts

- Redis executes commands **sequentially** (single-threaded per instance).
- Each **individual command is atomic**.
  - No race condition occurs *within* a single command.

---

## ⚠️ Multi-Command Operations Are NOT Atomic

When you use multiple Redis commands as part of one logical operation:

```text
ZCARD → check
ZADD  → insert
````

* These are executed as **separate commands**
* Other clients can interleave between them thus causing **race conditions** and **inconsistent state**.

### ❗ Result: Race Conditions

Example:

```text
limit = 5, current = 4

Request A → ZCARD → 4
Request B → ZCARD → 4

Request A → ZADD → 5
Request B → ZADD → 6 ❌ (limit exceeded)
```

---

## 🚀 Pipeline (Batching)

### What it does:

* Batches multiple commands into a **single network round trip**

### Benefits:

* Improves performance (reduced latency)

### Limitation:

* ❌ **NOT atomic**
* Commands can still interleave with other clients

> Pipeline = performance optimization, NOT correctness guarantee

---

## ⚡ Lua Scripts (Recommended for Atomic Logic)

### What it does:

* Executes multiple Redis operations as a **single atomic unit**
* Thus ensures operations either all succeed or all fail together incase of errors or crashes

### Benefits:

* ✅ Fully atomic (no interleaving)
* ✅ Supports conditional logic (`if/else`)
* ✅ Prevents race conditions
* ✅ Single round trip

### Behavior:

* While executing:

  * Redis is **temporarily blocked**
  * Other requests **wait in queue**

> Lua ensures: **check + modify happens together**

---

## 🔐 Locks (SET NX)

### What it does:

* Provides **mutual exclusion** across distributed systems. 
* A client can acquire a lock before executing critical section and release it afterward. Same like `locks` in traditional programming we do to prevent race conditions in concurrency scenarios (there lock is exclusive to a single process). But in distributed systems, we need `distributed locks` to coordinate access across multiple services/processes than a lock that is exclusive to a single process. For this we use Redis to implement distributed locks.

```bash
SET lock_key value NX EX 10
```

### Use cases:

* Prevent (race) multiple services from executing the same logic simultaneously
* Distributed coordination

### Benefits:

* ✅ Prevents race conditions across systems

### Drawbacks:

* ❌ Adds latency
* ❌ Reduces concurrency
* ❌ Requires careful handling:

  * Expiry
  * Failures
  * Retries

### Important:

* Lock itself is **not atomic logic**
* It only ensures:

  > “Only one client executes this block at a time”

---

## 🧠 When to Use What

### ✅ Single Redis Command

* Already atomic
* No extra handling needed

---

### ⚡ Use Lua Scripts when:

* You need **atomic execution of multiple Redis commands**
* It is a correctness tool for **state mutation** logic that involves multiple steps

* Example:

  * Rate limiting
  * Check + update logic
  * Conditional writes

> `Lua` cannot replace locks in scenarios involving `two services calling external API + DB update simultaneously`, where distributed coordination is required here we need `locks` (because logic is outside Redis, `Lua` only ensures atomicity within Redis, not across external systems).

---

### 🔐 Use Locks (SET NX) when:

* You need **coordination across distributed systems**
* Critical section involves:

  * External APIs
  * Databases
  * Background jobs

> `Locks` are not ideal for Redis atomic logic. `Locks` can technically enforce correctness for Redis operations, but they introduce overhead and reduce concurrency, so `Lua` is preferred for `atomic Redis logic`.

---

### ❗ Important Distinction

| Problem Type                          | Solution |
| ------------------------------------- | -------- |
| Combine Redis commands atomically     | Lua      |
| Coordinate multiple systems/processes | Lock     |

---

## ⚠️ Key Differences

| Feature                 | Lua Script | Lock (SET NX) |
| ----------------------- | ---------- | ------------- |
| Atomic execution        | ✅ Yes      | ❌ No          |
| Prevent race conditions | ✅ Yes      | ✅ Yes         |
| Works across systems    | ❌ No       | ✅ Yes         |
| Performance             | ✅ High     | ❌ Lower       |
| Complexity              | ✅ Low      | ❌ Higher      |

---

## 🧾 Summary

* **Atomicity** = no interleaving of operations, in db terms all operations succeed or fail together.
* **Race condition** = inconsistent state due to concurrent access

### Key Takeaways:

* Redis commands are atomic, but **multi-command logic is not**
* **Pipeline** improves performance, not correctness
* **Lua scripts**:

  * Best for atomic Redis logic
  * Prevent race conditions efficiently
* **Locks**:

  * Used for distributed coordination
  * Introduce overhead and complexity

---

## 🧠 One-Line Mental Model

> **Use Lua for atomic Redis logic, use locks for distributed coordination.**

---
