# Custody Observability, reference architecture

**What this is.** A complete specification for detecting the theft of an asset held under custody,
using systems an organisation already owns. It is written from a real case: an FBI counterintelligence
agent charged in August 2026 with taking $925,426 from a cryptocurrency wallet he was investigating,
undetected for roughly eighteen months until he confessed.

**Who it is for.** Anyone holding assets on behalf of an investigation, a court, a client or a
regulator. Law enforcement seizure units, custodians, exchanges, insolvency practitioners, escrow.
The pattern generalises to any asset that can be moved by the person guarding it.

**The claim, in one sentence.** The detection signal is not on the blockchain and not in the
employee's behaviour. It is the **absence of an authorisation** matching a movement that already
happened, and that is a database join, not an inference.

**Written 16 August 2026.** Case facts are from public reporting and the charging affidavit. The
individual is **charged, not convicted**. This is a reference architecture, not a description of any
agency's actual systems.

---

## 0. The one-paragraph version

A wallet under active investigation moved nearly a million dollars. The case system held no seizure
order, no authorisation, nothing that explained the movement. Those two facts arrived from
independent systems within minutes of each other and contradicted one another. Nobody joined them,
so the contradiction sat unexamined for eighteen months and was resolved by a confession rather than
a control. The architecture below is the join, plus enough discipline around it that the alarm is
worth reading.

---

## 1. The case

### 1.1 Verified facts

| Fact | Detail |
|---|---|
| Who | Patrick Steven Yaroch, former FBI supervisory special agent, counterintelligence |
| Charges | Interstate transportation of stolen property; receipt of stolen property |
| Amount | **$925,426.07** |
| Method | Accessed FBI systems, **memorised** the wallet recovery phrases, created his own wallet |
| Transfers | About ten, early 2025 |
| Target | An investigative subject from an adversarial nation, reported as Russia |
| Discovered | July 2026, when he contacted a DOJ official over Signal and confessed |
| Recovered | A Trezor hardware wallet and handwritten seed phrases |
| Stated motive | Frustration that the FBI "could not or would not act" against adversarial crypto accounts |
| Elapsed | Theft early 2025, self-report July 2026. **Roughly eighteen months** |

### 1.2 The detail that decides the architecture

**He memorised the seed phrases.** No file was copied, no email sent, no USB device used, nothing
downloaded. Every data-loss prevention control in existence would have seen precisely nothing,
because nothing left the building except a sequence of words inside a person's head.

That single fact eliminates most of what gets proposed after an incident like this. More endpoint
monitoring: nothing to catch. Stricter egress filtering: nothing to filter. Deeper file auditing: no
file. The only surviving signals are the **read event** on the key material and the **movement** of
the asset itself.

### 1.3 What it cost to find out

Eighteen months, and the mechanism was a conscience rather than a control. That is the number the
architecture is measured against, not against some theoretical ideal.

---

## 2. Why blockchain analytics alone could not have caught it

This section exists because the obvious first answer is wrong, and a compliance professional will
say so within one sentence.

**Chain analytics attributes at the SERVICE level.** Tools like Chainalysis, TRM Labs and Elliptic
cluster addresses and label the cluster: this belongs to Kraken, that belongs to a mixer, this one to
a sanctioned entity. That is what they are good at and it is genuinely hard.

What they cannot do is tell you the beneficial owner of a deposit address at an exchange. The
exchange knows, because the exchange did the KYC. The analytics vendor does not.

So the honest sequence is:

1. Chain analytics shows value leaving the subject wallet and arriving at an exchange deposit address.
2. That is all it shows. It names a service, not a person, and certainly not "an FBI agent".
3. Turning the deposit address into a name requires the **exchange's KYC records** and **legal
   process**. A subpoena, not an inference.

**Therefore chain analytics is a corroboration and attribution layer, not a detection layer.** It is
essential to the architecture and it is not the alarm.

**The alarm is internal.** The organisation already knew which wallet it was watching, because it was
investigating it. What it did not do was ask, at the moment of movement, whether anyone had
authorised that movement.

---

## 3. The governing idea

> **Every movement of an asset under custody must have a matching authorisation.
> No match is an incident.**

That is the whole system. Everything else is plumbing, corroboration or presentation.

### 3.1 Why this framing is better than "detect the insider"

- **It needs no behavioural model.** No profiling, no anomaly score on a person, no attempt to guess
  intent from travel or spending.
- **It is a join, not a judgement.** Two tables, one comparison, an answer in microseconds. There is
  nothing to tune and nothing to be wrong about.
- **It is auditable.** A reviewer can be shown the movement, shown the empty authorisation set, and
  agree or disagree in seconds.
- **It never watches an employee.** A person only appears once an asset has moved without permission.
  That distinction is the difference between a control a democracy will deploy and one it will not.

### 3.2 The precedent is not new

An evidence locker has enforced this rule for a century. Nothing leaves without a signed chit, and
the missing chit *is* the alarm. Nobody needs to identify the officer first.

Cryptocurrency held in an investigation is evidence in a locker. It happens to be a locker that
anyone holding the combination can open from home, at three in the morning, without the door making
a sound. The control did not become unnecessary. The door just stopped squeaking.

### 3.3 Double-entry, restated

Accounting solved a version of this in the fifteenth century. Luca Pacioli described double-entry
bookkeeping in Venice in 1494; Venetian merchants were already using it. Every movement has a
matching counter-entry, and an unmatched entry is an error by definition rather than by judgement.

Custody observability is that idea applied to evidence: every asset movement has a matching
authorisation, and an unmatched movement is an incident by definition.

---

## 4. The seven layers

```
01  SEE           sensors, all of them APIs the organisation already pays for
02  MOVE          transport, replayable, schema-enforced
03  AGREE         normalise to one vocabulary, resolve entities
04  HOLD          the stores: graph, relational, timeseries, object, cache
05  DECIDE        correlation and the deterministic rule
06  EXPLAIN       the model panel, out of band, advisory only
07  SHOW          the board, the queue, and an audit log of who looked
```

The join lives between **03** and **04**. That is the layer most organisations are missing, and it
is why they have all the data and none of the answer.

---

## 5. The stack, named

Thirty-eight components. One credible implementation per role, all of them commercially available or
open source. Nothing exotic.

### 5.1 Layer 01: SEE (12 components)

| Component | Role | Note |
|---|---|---|
| **Chainalysis KYT** | movement alerts on monitored wallets | the watchlist is the point, not the attribution |
| **TRM Labs** | second chain vendor | independent corroboration, different data and heuristics |
| **Elliptic Lens** | third opinion on attribution | optional; used where a single vendor's label is load-bearing |
| **Exchange APIs** | deposit attribution | legal process only, never a routine feed |
| **Case management** | open authorisations, seizure orders | **the other half of the join** |
| **CyberArk / Delinea** | privileged access and vault events | who opened the key material, and when |
| **Entra ID / Okta** | authentication events | who, from where, on what device |
| **CrowdStrike Falcon** | endpoint telemetry | process execution, USB, screen capture |
| **Splunk / Elastic** | the existing SIEM, as a source | do not rebuild it, read from it |
| **Travel + OGE 278e** | foreign travel and financial disclosure | slow signals, weeks not seconds |
| **Maltego** | OSINT link expansion | analyst-driven, not automated |
| **MISP** | shared indicators | community threat intel |

**Interface out:** webhook, REST poll, syslog, change data capture.

### 5.2 Layer 02: MOVE (4 components)

| Component | Role |
|---|---|
| **Kafka** | one topic per source, replayable from any offset |
| **Schema Registry** | Avro contracts, so a sensor cannot silently change shape |
| **Debezium** | change data capture from the case database |
| **Dead-letter queue** | nothing is dropped quietly |

The replay property matters more than it sounds. When a rule changes, you re-run history through it
rather than waiting for the next incident to find out whether it works.

**Interface out:** Avro over Kafka.

### 5.3 Layer 03: AGREE (4 components)

| Component | Role |
|---|---|
| **Flink** | stream jobs, windowing, the correlation window itself |
| **STIX 2.1** | one vocabulary for observables across a dozen sources |
| **Senzing / Zingg** | entity resolution: one person, many records |
| **dbt** | tested, versioned transforms |

**Entity resolution is where most of the difficulty actually lives.** The same officer appears as an
AD principal, an HR record, a case-system user id, a badge number and a name on a travel form. Until
those are one node, the second hop of the query returns nothing and the whole architecture is an
expensive way to store logs.

**Interface out:** Bolt, SQL, S3 put.

### 5.4 Layer 04: HOLD (5 components)

| Component | Role | Why this one |
|---|---|---|
| **Neo4j** | the property graph | multi-hop traversal, see §7 |
| **PostgreSQL** | authorisations, system of record | the authoritative answer to "was this permitted" |
| **ClickHouse** | event timeseries | volume; billions of rows, cheap scans |
| **MinIO + object lock** | evidence blobs, WORM | immutability is a legal requirement, not a preference |
| **Redis** | the hot correlation window | the last N minutes, in memory |

**Graph model.** Nodes: `Person`, `Case`, `Wallet`, `Address`, `AccessEvent`, `Authorisation`,
`Trip`, `ExchangeAccount`, `Device`. Edges: `READ`, `AUTHORISED`, `MOVED_TO`, `DEPOSITED_AT`,
`ASSIGNED_TO`, `TRAVELLED_TO`, `RESOLVES_TO`.

**Interface out:** Cypher traversal, policy query.

### 5.5 Layer 05: DECIDE (4 components)

| Component | Role |
|---|---|
| **Cypher** | the second hop: what else did this person touch |
| **Rule service** | `moved AND NOT authorised` in plain code, microseconds, no model |
| **Open Policy Agent** | "was this action permitted", expressed as versioned data |
| **Temporal** | durable workflow, so nothing is lost mid-incident |

**Open Policy Agent is the component most people leave out and the one that makes the rule
auditable.** Authorisation logic written into application code is a rule nobody can review. Written
as Rego, it is a file in git with a test suite, and a reviewer can read the policy without reading
the platform.

**Interface out:** incident JSON. Everything past this point is out of band.

### 5.6 Layer 06: EXPLAIN (3 components)

| Component | Role |
|---|---|
| **Four models, four vendors** | no shared failure domain |
| **Quorum + median** | three of four must agree on direction; the applied value is the median |
| **Qdrant** | prior incidents retrieved for context |

The panel **ranks** and **narrates**. It decides nothing. See §8 and the companion document
`FOUR_MODEL_CONSENSUS.md`.

**Interface out:** HTTPS, OIDC.

### 5.7 Layer 07: SHOW (6 components)

| Component | Role |
|---|---|
| **FastAPI** | the board and the queue |
| **Keycloak** | OIDC; who may see which case |
| **React + Vite** | assets against authorisations, mostly green |
| **Cytoscape.js** | click an amber row, get the subgraph |
| **Grafana + Loki** | is the pipeline itself alive |
| **Hash-chained audit log** | append-only record of who looked at what |

**The audit log is not optional.** A system that can surface an officer's activity must itself record
every access, or you have moved the insider risk rather than reduced it.

---

## 6. Triangulation, and why it is not "more alerts"

Every sensor in layer 01 fires constantly on its own. A monitoring programme dies the week its queue
stops being readable, and it stops being readable long before anyone admits it.

| Level | Condition | Action |
|---|---|---|
| **1, noise** | one signal | log it, alert on nothing |
| **2, alarm** | two **independent** sensors on the **same object** | a human looks today |
| **3, incident** | a third source agrees | open a file |

### 6.1 The arithmetic, honestly

Suppose a sensor has a false-positive rate of 1 in 1,000 events, and 100,000 events a day. Alone it
produces roughly 100 false alarms a day and is muted within a week.

Two **genuinely independent** sensors converging on the same object multiply: 1 in 1,000,000. The
same volume now yields roughly one false convergence per ten days. That is a readable queue.

**The word doing the work is "independent".** Two feeds derived from the same underlying log are one
sensor wearing two hats, and multiplying their error rates is arithmetic fraud. Chain movement (an
external vendor observing a public ledger) and case authorisation (an internal database of human
decisions) share no common cause, which is what makes their convergence meaningful.

### 6.2 What a contradiction is, and why it beats an anomaly

An anomaly says "this is unusual". Unusual things happen constantly and mean nothing.

A contradiction says "these two records cannot both be correct". The wallet moved **and** no
authorisation exists. One of those statements is false, or someone did something they were not
permitted to do. There is no third option, and that is why it is worth waking someone for.

---

## 7. Why a graph, specifically

If the only question were "did this wallet move without authorisation", a relational table would do
and a graph database would be architecture theatre. The graph earns its place on the **second hop**.

**First hop, trivial in SQL:**

```sql
SELECT w.id FROM movement m
LEFT JOIN authorisation a ON a.wallet = m.wallet
  AND m.ts BETWEEN a.valid_from AND a.valid_to
WHERE a.id IS NULL;
```

**Second hop, the one that finds a person:**

> *Did anyone who read the key material for this case also do anything else worth a look?*

```cypher
MATCH (w:Wallet {id:$wallet})<-[:FOR]-(c:Case)
MATCH (p:Person)-[r:READ]->(k:KeyMaterial)-[:FOR]->(c)
WHERE NOT EXISTS {
  MATCH (p)-[:AUTHORISED]->(a:Authorisation)-[:COVERS]->(w)
  WHERE r.ts >= a.valid_from AND r.ts <= a.valid_to
}
OPTIONAL MATCH (p)-[:TRAVELLED_TO]->(t:Trip) WHERE t.declared = false
OPTIONAL MATCH (p)-[:OWNS]->(x:ExchangeAccount)-[:RECEIVED]->(:Address)<-[:MOVED_TO]-(w)
RETURN p, r, collect(DISTINCT t), collect(DISTINCT x);
```

In SQL that is four joins with two anti-joins and it gets worse with every hop. In Cypher it is one
traversal that reads roughly like the sentence a human would say. That readability is not cosmetic:
a rule an investigator can read is a rule an investigator can challenge.

---

## 8. Where the models sit, and where they do not

**Never in the decision path.** A model call is 300ms to 60s and can rate-limit. The rule that
decides whether an incident exists is arithmetic and runs in microseconds. Putting a model there
adds latency and opinions to a comparison that needs neither.

**Out of band, they do the thing arithmetic cannot:** triage a queue by likely importance, write the
narrative a human will read at 7am, and notice when two incidents look like one campaign.

Four models from four vendors, because a rate limit is provider-wide and a blind spot is
family-wide. Three of four must agree on the direction of any proposed change; the applied value is
the median so one confident model cannot drag it; and any change over 25% is refused.

**Both failure directions are asserted by test:** an unavailable panel cannot block a real alarm, and
an agreeable panel cannot dismiss one.

Full treatment in `FOUR_MODEL_CONSENSUS.md`.

---

## 9. The trace: this case, through this system

| # | Sensor | What fires | Level |
|---|---|---|---|
| 1 | Chain analytics | A wallet under active investigation moves, early 2025 | 1, noise |
| 2 | Case system | No open authorisation covers that wallet at that time | **2, alarm** |
| 3 | Correlation graph | Both records resolve to the same `Wallet` and the same `Case`, minutes apart | alarm confirmed |
| 4 | Triangulation | Two independent sources, one object, a contradiction | escalate |
| 5 | Rule service | `moved AND NOT authorised` → incident, in microseconds | **incident** |
| 6 | Privileged access log | A named officer read the key material outside any authorised window | **3, person identified** |
| 7 | Exchange KYC | Deposit address resolves to an account holder. Subpoena, not analytics | attributed |
| 8 | Model panel | Ranked against everything else in the queue, written up | advisory |
| 9 | Board | One amber row on an otherwise green screen | delivered |

**Elapsed, steps 1 to 5: minutes.** Steps 6 and 7 take as long as an access-log query and a legal
request take, which is days rather than months.

**Employees surveilled to reach step 6: zero.** The officer's name is produced by asking who read a
specific piece of key material for a specific case, after that case's asset had already moved
without permission. No one was watched. A question was asked about a record.

---

## 10. Legal and ethical boundaries

### 10.1 The design choice that makes this deployable

**Monitor the evidence, not the people.** The system watches assets under custody and the
authorisations that should accompany them. It holds no behavioural baseline for any employee and
produces no score for any person. A person enters the picture only after an asset has moved without
an authorisation, at which point the question is narrow, specific and evidenced.

This is not a softer version of insider-threat monitoring. It is a different thing with a different
legal posture, and it is the reason the architecture survives a works council, a privacy regulator
and a defence lawyer.

### 10.2 IP addresses and personal data

An IP address is personal data under GDPR, confirmed by the CJEU in *Breyer* (C-582/14). Where the
architecture records network sources, truncate on the way **in** (a /24 or /48), so a later bug in a
query cannot leak what was never stored.

### 10.3 What is never done, and why

| Never | Why |
|---|---|
| Scanning or probing a suspect's infrastructure | Criminal: StGB §202a, §202b, §303a, §303b (and §202c criminalises possessing the tooling with that intent), EU Directive 2013/40, US CFAA §1030, Canada CC s.342.1 |
| Commercial spyware against staff | Legally untenable against employees; NSO has sat on the US Commerce Entity List since 2021 |
| AI deception detection on personnel | See §10.4 |
| Hack-back of any kind | Criminal as above; the address is usually a compromised third party; and it converts a victim into a defendant |

### 10.4 Why deception-detection AI is refused specifically

It is the most commonly proposed answer to insider risk and it fails on base rates.

The US National Research Council's 2003 review put polygraph accuracy at a median index of about
0.86 and rated the underlying evidence quality **low**. Its central conclusion was that screening at
**low prevalence produces overwhelmingly false positives**. If one employee in ten thousand is
stealing, a test at that accuracy flags hundreds of honest people for every guilty one.

RAND's work on Analysis of Competing Hypotheses points the same way: structure imposed by a system
reduces bias in people **without** an intelligence background, and does not measurably help those
with one. The lesson is to build the structure into the process, not to test the person.

An architecture that flags hundreds of innocent colleagues to find one thief does not survive
contact with an employment tribunal, and it should not.

---

## 11. Implementation notes

### 11.1 Build order

1. **The authorisation record first.** If "was this permitted" cannot be answered from a database,
   nothing downstream can work. This is usually the hardest and least glamorous step, because the
   answer often lives in a PDF or a person's memory.
2. **The movement feed second.** One chain vendor is enough to begin.
3. **The join third**, as a nightly batch. Run it over the last two years of history before it ever
   runs live. That backfill is the cheapest possible test of whether the data supports the rule.
4. **Entity resolution fourth.** Only now does the second hop become possible.
5. **The graph fifth**, once you have more than two entity types worth traversing.
6. **The panel last**, advisory only, printing to a log nobody acts on, for at least a month.

### 11.2 Failure modes to expect

| Failure | Cause | Mitigation |
|---|---|---|
| Authorisations exist but are not machine-readable | signed PDFs, email approvals | a structured authorisation record is a prerequisite, not a nice-to-have |
| Clock skew produces phantom incidents | movement timestamped before its authorisation | a tolerance window, sized from measured skew, not guessed |
| An authorisation is entered after the fact | the control becomes retrospective paperwork | authorisations are append-only and timestamped by the system, never by the user |
| Entity resolution merges two people | shared name, shared device | resolution must be reviewable and reversible, with an audit trail |
| The queue is ignored | too many level-1 alerts promoted | nothing below level 2 reaches a human, ever |

### 11.3 The check that must exist from day one

**Backfill the rule over history and count what it would have produced.** A rule that fires on
40 events a day is not a control, it is a new source of noise. A rule that fires on nothing over two
years is either perfect or broken, and the way to tell is to inject a synthetic unauthorised movement
and confirm the rule catches it. A gate that only ever goes green is unproven.

---

## 12. Honest limits

- **This would not have prevented the theft.** It would have detected it, in minutes rather than
  eighteen months, with the money still sitting untouched in an exchange account. Prevention is a
  different control: dual authorisation on key material, so no single officer can read a seed phrase
  alone.
- **It depends entirely on the authorisation record being trustworthy.** An organisation where
  authorisations are back-dated has moved the problem rather than solved it.
- **The second hop is only as good as entity resolution.** Get that wrong and the graph is a slower
  way to store rows.
- **Chain analytics is a corroboration layer with real error rates.** Attribution labels are
  probabilistic and vendors disagree, which is exactly why more than one is listed.
- **None of this is benchmarked against a named product.** The argument here is architectural and
  every part of it is checkable; no superiority claim is made or intended.
- **Nothing here describes any agency's actual systems.** It is what the public record suggests was
  missing, expressed as components that exist.

---

## 13. Artifacts

| File | What it is |
|---|---|
| `marketing/Custody_Observability_3D.html` | The animated 3D architecture. Twelve nodes, seven layers, the nine-step trace. Single file, three.js from CDN, opens with a double-click |
| `marketing/Insider_Custody_Observability.html` | The 2D version of the same, lighter and better for screenshots |
| `docs/FOUR_MODEL_CONSENSUS.md` | The model panel in full: CI/CD, defence and release notes |
| `docs/SECURITY_ARCHITECTURE.md` | What we run, what we do not have, what to add |

---

## 14. Sources

- [NBC News](https://www.nbcnews.com/politics/justice-department/feds-charge-fbi-agent-say-stole-nearly-one-million-crypto-russia-rcna590674), charges, the reported adversarial nation
- [CNN](https://www.cnn.com/2026/08/03/politics/fbi-agent-accused-stealing-cryptocurrency), timeline, the ChatGPT queries, the confession
- [WUSA9](https://www.wusa9.com/article/news/crime/former-fbi-supervisor-charged-with-stealing-cryptocurrency/65-09459ba7-059d-4ea6-a475-813436c528a0), the $925,426.07 figure, memorised seed phrases, the Trezor
- National Research Council, *The Polygraph and Lie Detection* (2003), accuracy index and the base-rate conclusion
- CJEU, *Breyer v Bundesrepublik Deutschland* (C-582/14), dynamic IP addresses as personal data

---

*Written 16 August 2026. Every component named is commercially available or open source. The
individual named in §1 is charged, not convicted.*
