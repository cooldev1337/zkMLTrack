Verifiable-AI-Model-Versioning

This project proposes a system for verifiable model version control, where users can register AI models and prove — without revealing the model — that they reach a certain accuracy on a public validation dataset.
The problem we target is the lack of transparency in AI model claims (accuracy, performance, etc.), where developers can say “my model is 99% accurate” without anyone being able to verify it.
We aim to solve this using Merkle proofs, zkML (EZKL), and smart contracts on Arbitrum Stylus, allowing anyone to verify accuracy on-chain while models remain private.

During the time available, we built a partial but functional prototype, focusing mainly on the backend. We implemented:

A local backend with endpoints to receive ONNX models, run EZKL tools, and generate proofs.

Automated generation of circuits, witnesses, proofs, and verifiers using EZKL.

Deployment of EZKL-generated verifier contracts to Arbitrum Stylus using Rust (only requiring RPC + account in .env).

A partial workflow to register verifier metadata to a main controller contract (almost complete, but missing final integration).

A basic frontend intended for model uploads (incomplete but scaffolded).

Several experiments stored in pruebas/, including Solidity prototypes for a Main Controller, Merkle inclusion verification logic, and unfinished tests.

The full system was not completed, but we achieved a working foundation and gained essential experience with EZKL, Stylus Rust contracts, Merkle proofs, and verifiable ML flows.

## Prerequisites

To run the prototype locally:

Python 3.10 - 3.12

Rust + cargo

EZKL installed locally

Arbitrum Stylus toolchain

Optional: local Arbitrum Nitro dev node or RPC provider (Infura, Alchemy)

## Project Structure

```
Verifiable-AI-Model-Versioning/
├── backend/                      # Backend (Flask): EZKL flow, verifier deployment, endpoints
│   ├── app.py                    # Main Flask server with endpoints
│   ├── ezkl_tools/               # Scripts wrapping EZKL CLI calls
│   ├── stylus_deployer/          # Rust contract deployment utilities
│   └── models/                   # Temp storage for ONNX files
│
├── frontend/                     # Frontend UI (WIP)
│   ├── upload/                   # Page for user to upload ONNX models
│   └── resources/                # Scripts and assets (incomplete)
│
├── pruebas/                      # Experiments and prototypes
│   ├── solidity/                 # MainController example, Merkle tests, unfinished verifier logic
│   ├── ezkl-tests/               # EZKL experiments, witness generation tests
│   └── misc/                     # Other attempts that were not integrated
│
└── README.md
```

## Implementation Overview

Below is a clear explanation of what each major component does in the prototype.

### Backend (Flask)

This is the core of the prototype and the most complete part.

**Main capabilities implemented:**

✔ **Receive ONNX model from user**

Stores uploaded .onnx files to the backend temporarily.

✔ **Generate entire zkML pipeline using EZKL**

Backend scripts automate:

* `ezkl compile`
* `ezkl gen-witness`
* `ezkl prove`
* Building verifier contract artifacts

✔ **Deploy EZKL Verifier contract**

A deployment script sends the compiled verifier to a network.
Just configure in `.env`:

```
RPC_URL=
PRIVATE_KEY=
CHAIN_ID=
```

✔ **Partially implemented: Register model attributes**

An endpoint exists to:

* send the deployed verifier address
* send the claimed accuracy
* attach metadata

But final call to the MainController (Stylus contract) is missing integration logic.

### Frontend

**Planned role:**

* Simple interface to upload ONNX models.
* Trigger backend generation flow.
* Display verification outputs.
* Later: show leaderboard of best models.

**Progress:**

* Basic upload UI exists.
* No integration with backend yet.

### Pruebas/

Experimental folder showing what was attempted during development:

#### 1. Solidity Main Controller (prototype)

Contract meant to:

* allow owner to create "tasks"
* map tasks → multiple verifier contracts
* keep best model accuracy
* verify Merkle inclusion proofs (Poseidon)

Missing:

* integration with EZKL verification
* final on-chain flow

#### 2. Merkle proofs experiments

Tests on how to:

* hash dataset rows
* generate Merkle tree from CSV
* verify inclusion with OpenZeppelin

#### 3. EZKL isolated tests

Trying different circuits, witness formats, and model sizes.

These experiments were essential to understand constraints and flows but were not integrated into the final prototype.

---

## Full System Goal (What We Intended to Build)

Below is the high-level flow we originally aimed to implement, divided into phases.

### **PHASE 1 — Core Infrastructure**

* Upload validation dataset to Filecoin.
* Compute Merkle tree over dataset rows using Poseidon.
* Deploy MainController on Stylus storing Merkle root.

### **PHASE 2 — Model & Proof Integration**

* User trains model locally, exports to ONNX.
* User generates zk-proof of model accuracy using EZKL:

  * compile → generate witness → prove → export verifier
* Backend deploys verifier contract on Stylus.
* Backend registers verifier address + accuracy to MainController.

### **PHASE 3 — Verifiable Accuracy Validation**

* Chainlink VRF selects random samples from dataset.
* User generates Merkle inclusion proofs for samples.
* User generates zk-proofs for model outputs on those samples.
* Verifier contract checks:

  * correctness of witness/proof
  * inclusion in Merkle tree
* MainController updates best accuracy.

### **PHASE 4 — Frontend & Usability**

* User uploads new models.
* User generates proofs.
* Backend deploys verifier.
* Users see leaderboard of best-performing models.

---

## System Diagram
