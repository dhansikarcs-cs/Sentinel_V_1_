# Sentinel — Secure Transport & Clinic Storage

*Decision doc for the IRL data path: physical ring → cloud → clinic's local server.
Complements `docs/ROADMAP_HARDWARE.md` (that covers ingestion into `POST /ring/data` —
this covers the network path *after* ingestion). Many candidate ideas, each with a
SWOT analysis. No code changes yet — this is a brainstorm to pick a direction.
Rev 2 incorporates reviewer feedback: Transport Constitution, Perfect Forward Secrecy,
dead-letter queue, zero-metadata routing, clinic ACK protocol, multi-clinic routing,
and a threat → control mapping.*

## 1. Context & the data lifecycle

Today (dev/laptop): `ring → BLE/vendor adapter → POST /ring/data → Render DB`.

IRL (production): the ring stays on the patient 24/7, so readings originate wherever
the patient is, not at the clinic. The clinic's **local server** is the canonical store.
The cloud is **Secure Transport Layer (STL) — transport only**, never a home for PHI.

```
ring ──BLE── patient phone ─┐
                            ├──(E2EE)──► Secure Transport Layer (STL) ──(pull+ACK)──► clinic local server
ring ──vendor cloud── bridge┘           (store-and-forward, zero-knowledge,            (canonical store
                                         ciphertext only, auto-delete after ACK)        + Ollama AI, offline)
```

Two coexisting modes:
- **Dev/demo mode (current):** cloud (Render) is primary; clinic server not involved.
- **IRL mode (target):** clinic server is primary; STL is transport only.

**The philosophy, in one line:** *cloud transports, clinic owns.*

## 2. Sentinel Transport Constitution

The equivalent of the Architecture Constitution, but for hardware communication.
Every option in this document is judged against these — a proposal that fails any
of the first nine is not "negotiable later"; it is rejected.

1. The cloud (STL) SHALL NEVER permanently store PHI.
2. The STL SHALL NEVER decrypt patient data — it forwards ciphertext only.
3. The clinic SHALL always own and retain patient records.
4. Transport SHALL be stateless whenever possible (no session DB at the STL).
5. End-to-end encryption SHALL begin on the patient's device (phone/gateway), before any network hop.
6. Only clinic-held private keys SHALL be able to decrypt health data.
7. The STL SHALL auto-delete ciphertext after the clinic acknowledges it.
8. Offline operation SHALL always be supported — no data may be lost on any single outage.
9. The STL SHALL reveal minimal metadata: opaque destination token, ciphertext, timestamp, nonce — nothing else.
10. All transport decisions SHALL favour clinician + patient privacy over convenience.

## 3. The recommended shape: STL protocol (D + B)

**Phone (BLE gateway) → E2EE → Secure Transport Layer → clinic pull → local store.**
This is the default direction; all other candidates in §4 are comparisons/fallbacks.

### 3.1 The full lifecycle (with clinic ACK)

```
Phone          STL                      Clinic
 │              │                          │
 ├─ push batch ─► store ciphertext         │      phone keeps its own copy until ACK
 │              │ ◄────── pull /pending ───┤      clinic polls every ~10 s (no inbound ports)
 │              │ ──── batch (ciphertext) ─►      clinic decrypts LOCALLY
 │              │                          ├─ verify per-device hash-chain + signature
 │              │ ◄─────── ACK ────────────┤
 │              ├─ delete ciphertext       │
 │◄── ACK (next sync) ─────────────────────┤
 ├─ clear local queue                      │
```

- **No ACK → keep retrying.** The clinic keeps polling; the phone keeps its encrypted
  queue until it learns the clinic stored the batch.
- **Dead-letter:** the STL retains un-ACKed ciphertext for a bounded window (48 h),
  then deletes it. Never infinite. Data is not lost because the *phone* retains the
  batch until ACK — the dead-letter is STL hygiene, not the durability guarantee.
- **Push stays narrow:** push is reserved for non-PHI crisis flags (e.g. "patient X
  has an active crisis", email/WebSocket/tunnel), so alert latency stays seconds while
  PHI flows at pull cadence.

### 3.2 Pull, not push

Clinic server initiates `GET /pending` + `DELETE` on ACK. Benefits: no public IP, no
inbound firewall rules, no DMZ, no NAT headaches, easier to get approved by hospital IT.

### 3.3 Zero-metadata routing & multi-clinic

The STL routes by an **opaque destination token** (a random per-clinic UUID — never a
name). It cannot reverse the token into a clinic/patient/psychologist identity. The same
relay therefore serves **Clinic A, B, C … hospitals, private practices, NGOs,
universities** without redesign — each is just another token with its own queue. The STL
sees only:

```
destination_token (opaque)  ciphertext  timestamp  nonce  (per-device sequence)
```

### 3.4 Perfect Forward Secrecy

Every upload session uses an **ephemeral ECDH key** (X25519) that lives only for that
session:

```
phone:  ephemeral priv (gen) → ECDH(clinic_pub) → session key → AES-256-GCM → destroy ephemeral
clinic: ECDH(ephemeral_pub, clinic_priv) → same session key → decrypt → nothing to store
```

Even if today's device key leaks, yesterday's data stays unreadable. Offline batches
use one ephemeral key per batch, destroyed after use.

### 3.5 Offline-first

Ring → phone with no internet: readings are **encrypted at rest on the phone** and queued.
When connectivity returns, the phone sends the batch through the same path. Sentinel was
built offline-first (Ollama local, offline crisis); transport inherits that.

## 4. Candidate architectures (many ideas, with SWOT)

### A. Direct to clinic — no cloud at all
BLE bridge (clinic LAN gateway or patient phone) sends straight to the clinic server over LAN / WireGuard.

```
ring ──BLE──► phone/gateway ──WireGuard/LAN──► clinic server
```
- **Strengths:** simplest threat model; PHI never leaves clinic network; zero cloud cost; matches the existing "run fully offline with Ollama + SQLite" design.
- **Weaknesses:** patients away from the clinic are unreachable — no remote monitoring; clinic still needs tunnel/ingress; single clinic dependency.
- **Opportunities:** ideal fallback and baseline; strongest for the crisis/offline story.
- **Threats:** remote patients → no data → false "silent patient" signal (now connectivity, not behavior).

### B. Stateless zero-knowledge STL + clinic pull (recommended — §3)
- **Strengths:** STL is zero-knowledge by construction (no plaintext, no keys); clinic needs no public IP — it *pulls*; bounded STL storage (lifecycle + dead-letter) → cheap and private; survives clinic downtime via phone retention + ACK; fits existing `/ring/data` device-token auth unchanged.
- **Weaknesses:** minutes-scale PHI latency (fine for rings; crisis flags ride the push channel instead); needs a polling client + queue monitoring at the clinic; needs cert/key lifecycle management.
- **Opportunities:** ACK protocol + dead-letter make it production-grade; scales to multi-clinic, hospitals, NGOs with no redesign (token routing).
- **Threats:** lost phone (see §7 controls), corrupted queue, replay/MITM, certificate expiry, key compromise — all mitigated in §7.

### C. Cloud primary + encrypted replication to clinic
- **Strengths:** zero rework of current deploy; immediate availability; clinic gets a local copy for offline AI/analysis.
- **Weaknesses:** cloud holds PHI — weakest posture; contradicts the constitution ("cloud never stores PHI").
- **Opportunities:** as a *backup* of A/B (clinic→cloud replication) it's a valid safety net; fine for demo mode.
- **Threats:** regulatory exposure; weak grant/compliance claim.

### D. Phone gateway (portable BLE bridge) — likely required, pairs with A or B
- **Strengths:** ring is truly portable (24/7); no per-clinic hardware; phone already hosts the vendor app (Jport) → SDK path exists; offline queue lives on the phone.
- **Weaknesses:** battery/OS/permission friction; phone is a new attack surface; lost/upgraded phones need key + token rotation.
- **Opportunities:** reuse `BLEGATTRingSource` in a small native app or PWA; camera-PPG fallback (JUDGE_QA) rides the same channel.
- **Threats:** patient friction; PHI encrypted-at-rest on the phone is mandatory (constitution #5).

### E. Vendor-cloud passthrough (Jport path)
- **Strengths:** fastest M1 path (no BLE spec sheet needed); vendor handles sync/backfill.
- **Weaknesses:** vendor sees plaintext; foreign jurisdiction; only viable interim. Violates constitution unless instantly re-encrypted (vendor already saw it).
- **Opportunities:** real data now; disable later.
- **Threats:** vendor outage/ToS/quality; may expose only aggregates, not raw signals.

### F. Managed SaaS + clinic read-only replica
- **Strengths:** least engineering.
- **Weaknesses:** cloud is the store, not the clinic — fails the constitution.
- **Opportunities:** interim demo/deploy posture (current Render setup).
- **Threats:** lock-in, cost, worst compliance story. Listed for completeness only.

### G. Air-gapped / manual fallback (no connectivity)
- **Strengths:** works with zero infrastructure; continuity for rare no-network cases.
- **Weaknesses:** manual, not 24/7, human-in-the-loop.
- **Opportunities:** a documented emergency procedure strengthens the design for regulators.
- **Threats:** portable media is a leak surface — encrypt it (constitution #5).

### H. Confidential-computing STL (TEE)
- **Strengths:** attestable zero-knowledge; STL could shape/route inside an enclave without plaintext reaching the platform.
- **Weaknesses:** ops overhead; attestation setup; overkill when §3 E2EE already covers routing.
- **Opportunities:** differentiator for the paper/pitch ("attestable zero-knowledge transport").
- **Threats:** enclave escape; complexity at pilot scale.

## 5. Transport & security mechanisms

Stackable across architectures:

1. **E2EE at the source** — phone/gateway encrypts with the clinic public key (`age` X25519 or RSA-OAEP per batch). STL sees only ciphertext + routing metadata.
2. **Envelope encryption** — gateway holds a per-session data key (AES-256-GCM); clinic master key wraps it. Rotating the master key re-wraps data keys without re-encrypting PHI.
3. **Perfect Forward Secrecy** — ephemeral ECDH per session/batch (§3.4); session keys destroyed after use.
4. **mTLS per device** — optional X.509 identity for gateways; STL and clinic both verify. Stronger than bearer tokens, heavier to provision at M1 scale.
5. **Device-token rotation** — extend existing `X-Device-Serial/Token` (SHA-256 at rest, constant-time) over TLS 1.3; rotate on schedule + instantly on `POST /ring/unpair`.
6. **Per-device sequence + hash-chain** — each reading references the previous hash + monotonic counter → tamper-evident stream (mirrors the existing hash-chained audit log). Clinic verifies on decrypt.
7. **Signed batches** — Ed25519 batch signatures → clinic verifies origin even if a token leaked.
8. **Pull-based transport** — clinic `GET /pending` → `DELETE` on ACK. No inbound firewall rules, no public IP.
9. **Zero-trust tunnel (optional)** — Tailscale/WireGuard mesh for the clinic → push/lower latency without inbound ports.
10. **Just-in-time STL** — serverless function + object storage with lifecycle rule; no persistent DB at the STL.
11. **Field-level encryption at the clinic** — reuse Fernet so the most sensitive DB fields stay ciphertext at rest.
12. **Data minimization** — raw signals only as long as needed; derive features/aggregates; minimize PII in the envelope.
13. **Replay protection** — timestamp + nonce + per-device sequence; STL dedupes by (token, seq); clinic rejects out-of-order.
14. **Rate limiting + anomaly** — reuse `RateLimiterMiddleware`; abnormal push cadence flagged (stolen device spamming is itself a signal).
15. **2-of-2 key ceremony** — clinic master key split across two key holders; lost key recoverable, single compromised holder is not.
16. **Post-quantum readiness** — plan ML-KEM/Kyber key-exchange upgrade (medical records live decades); note in roadmap, don't block on it.

## 6. Consolidated SWOT (architecture level)

| # | Idea | Strengths | Weaknesses | Opportunities | Threats |
|---|------|-----------|------------|---------------|---------|
| A | Direct to clinic (no cloud) | PHI never leaves clinic; offline-first | No remote coverage; needs tunnel anyway | Baseline + fallback | Remote patients invisible → false "silent" |
| **B** | **STL + clinic pull (§3)** | **Zero-knowledge; no public IP; cheap; survives clinic downtime; scales multi-clinic** | **Latency; queue/retry/monitoring/cert upkeep** | **ACK + dead-letter make it production-grade** | **Lost phone; replay; MITM; cert expiry (all → §7)** |
| C | Cloud primary + replication | No rework; immediate; local copy for AI | Cloud holds PHI; fails constitution | Backup net for A/B | Breach exposure; weak compliance claim |
| D | Phone gateway | True 24/7 portability; reuses BLE adapter | Battery/OS/permissions; new attack surface | M1 path; camera-PPG fallback | Friction; encrypted-at-rest mandatory |
| E | Vendor-cloud passthrough | Fastest M1; no BLE spec needed | Vendor saw plaintext; foreign jurisdiction | Real data now; disable later | Vendor outage/ToS; aggregates only |
| F | Managed SaaS + replica | Least engineering | Not "store at clinic"; lock-in | Interim demo posture | Worst compliance story |
| G | Air-gap fallback | Works anywhere; simple | Not 24/7; human-in-the-loop | Regulator-friendly documented fallback | Stolen portable media |
| H | TEE STL | Attestable zero-knowledge; smart routing | Ops overhead; overkill for B | Pitch/paper differentiator | Enclave escape; complexity |

## 7. Threat → control mapping

The reviewer's threat list, answered with concrete controls:

| Threat | Control |
|--------|---------|
| **Lost / stolen phone** | Encrypted-at-rest queue (device unlock + app-level encryption, constitution #5); remote wipe on unpair; instant device-token revocation. |
| **Corrupted queue** | Per-batch hash-chain + sequence; corruption detected on decrypt and re-requested; clinic rejects invalid batches. |
| **Replay attacks** | Per-device monotonic sequence + nonce + timestamp; STL dedupes (token, seq); clinic rejects out-of-order. |
| **MITM** | TLS 1.3 on every hop; mTLS/pinning on the STL↔clinic link; E2EE means a MITM still reads nothing. |
| **Certificate expiry** | Short-lived certs, automated renewal (ACME or internal CA), expiry alerting in STL monitoring. |
| **Key compromise** | PFS limits blast radius to one session; rotate device tokens; re-wrap with new master key; zero-knowledge STL means cloud compromise yields nothing readable. |
| **STL outage** | Phone offline-first queue + clinic keeps polling; ACK-gated deletion → nothing lost. |
| **Clinic down > purge window** | Phone retains every batch until ACK, so 48 h dead-letter at the STL never causes loss; clinic resumes where it left off (sequence numbers). |

## 8. Comparison matrix

| Criterion | A direct | **B STL+pull** | C cloud-primary | D phone | E vendor | F SaaS | G air-gap | H TEE |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Zero-knowledge cloud | — | ✅ | ❌ | ✅* | ❌ | ❌ | ✅ | ✅ |
| 24/7 remote coverage | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| No inbound clinic ports | ✅ (tunnel) | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| PHI stored only at clinic | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Fits current codebase | ✅ | ✅ (no change) | ✅ | ✅ | ✅ | ✅ | — | ⚠️ |
| Ops cost | low | med | low | low | low | high | low | high |
| Offline resilience | ✅ | ✅ (buffer+ACK) | ⚠️ | ✅ | ❌ | ❌ | ✅ | ⚠️ |
| Crisis-alert latency | best | ⚠️ (push channel) | best | ⚠️ | ⚠️ | best | ❌ | good |
| Multi-clinic ready | ⚠️ | ✅ (token routing) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Complexity | low | med | low | med | med | low | low | high |

*\*Phone must encrypt before upload (D + B together).*

**Recommended shape (Sept 2026 pilot):** **D + B** — phone/gateway BLE bridge, E2EE
envelope + PFS, stateless STL, clinic pull + ACK, dead-letter, tunnel/push for crisis
flags, air-gap (G) as documented fallback. Revisit E only if the Jport BLE spec is
unavailable and the vendor cloud is the only option.

## 9. Phased recommendation

- **Phase 1 (now, laptop dev):** no change. HTTPS + device-token `/ring/data` already secure. Mock the STL interface so nothing downstream depends on it.
- **Phase 2 (first real ring, M1):** confirm interface (Jport spec sheet); stand up the STL as a minimal serverless store-and-forward + clinic pull client + ACK; keep vendor passthrough (E) as interim adapter if BLE is not ready.
- **Phase 3 (pilot, 30 rings, M3):** ship phone gateway (D) with encrypted-at-rest buffering; E2EE envelope + PFS; key ceremony (2-of-2); per-device hash-chain; dead-letter + monitoring; crisis push channel; air-gap procedure; cert lifecycle automation.
- **Engineering work items (the reviewer's weaknesses, made concrete):** queue management, retry/ACK logic, relay/STL monitoring, certificate + key rotation lifecycle, device-token rotation tooling, phone app key management.
- **Always:** clinic runs Ollama locally (already designed) so AI works offline; STL never has plaintext.

## 10. Risks & open questions

1. Does the Jport ring have Wi-Fi or only BLE (→ phone required)? (ROADMAP_HARDWARE open question #4.)
2. Does the Jport cloud expose raw signals or only aggregates? (determines E viability.)
3. Clinic internet reliability → pull cadence + purge window vs outage tolerance → buffering size.
4. Who are the two key holders at the clinic?
5. Do we ship a tiny native phone app or a PWA (Expo/BluetoothWeb) for the gateway?
6. Live-crisis latency: is "alert in seconds, PHI in minutes" acceptable? (recommend: yes — push flags, pull data.)
7. ACK lifecycle: where do we put the per-batch manifest so the clinic can resume a mid-batch outage cleanly?
