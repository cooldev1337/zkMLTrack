import hashlib
import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import asyncio
import ezkl
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from web3 import Web3
from dotenv import load_dotenv
from solcx import compile_standard, get_installed_solc_versions, install_solc
from hexbytes import HexBytes

load_dotenv()

APP_ROOT = os.environ.get("ARTIFACTS_ROOT", os.path.join(os.getcwd(), "artifacts"))
VALIDATION_CSV = os.environ.get("VALIDATION_CSV", "iris_test_split.csv")
CALIBRATION_SAMPLES = int(os.environ.get("CALIBRATION_SAMPLES", "5"))
GENERAL_CONTRACT_ADDRESS = os.environ.get("GENERAL_CONTRACT_ADDRESS")
GENERAL_CONTRACT_ABI_PATH = os.environ.get("GENERAL_CONTRACT_ABI_PATH", "../Verifier.abi")
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER")
WEB3_OPERATOR_KEY = os.environ.get("WEB3_OPERATOR_KEY")
SOLC_VERSION = os.environ.get("SOLC_VERSION", "0.8.20")
REGISTRY_FUNCTION_NAME = os.environ.get("REGISTRY_FUNCTION_NAME", "../registerModel")

app = Flask(__name__)


# ---------------------------- helpers -------------------------------------

def ensure_dir(path: str) -> None:
    """Create the directory path if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def task_paths(task_id: str) -> Dict[str, str]:
    """Return all artifact paths for a given task id."""
    base = os.path.join(APP_ROOT, task_id)
    ensure_dir(base)
    return {
        "base": base,
        "model": os.path.join(base, "network.onnx"),
        "settings": os.path.join(base, "settings.json"),
        "calibration": os.path.join(base, "calibration.json"),
        "compiled": os.path.join(base, "network.ezkl"),
        "srs": os.path.join(base, "kzg.srs"),
        "witness": os.path.join(base, "witness.json"),
        "input": os.path.join(base, "input.json"),
        "pk": os.path.join(base, "test.pk"),
        "vk": os.path.join(base, "test.vk"),
        "proof": os.path.join(base, "test.pf"),
        "status": os.path.join(base, "status.json"),
        "verifier_sol": os.path.join(base, "Verifier.sol"),
        "verifier_abi": os.path.join(base, "Verifier.abi"),
    }


def load_validation_dataframe() -> pd.DataFrame:
    """Return the full validation dataframe (features + label)."""
    if not os.path.isfile(VALIDATION_CSV):
        raise FileNotFoundError(
            f"Validation CSV not found at {VALIDATION_CSV}. Generate it via the notebook first."
        )
    df = pd.read_csv(VALIDATION_CSV)
    if df.shape[1] < 2:
        raise ValueError("Validation CSV must contain at least one feature column and one label column")
    return df


def pick_validation_sample(df: pd.DataFrame) -> tuple[np.ndarray, object]:
    """Return a random feature row and its label from the validation CSV."""
    sample = df.sample(n=1, random_state=random.randint(0, 1_000_000))
    features = sample.iloc[:, :-1].values.astype(np.float32)
    label = sample.iloc[:, -1].iloc[0]
    return features, label


def build_label_index_map(df: pd.DataFrame) -> Dict[object, int]:
    """Create a mapping from label value to index (sorted for determinism)."""
    labels = sorted(df.iloc[:, -1].unique())
    return {label: idx for idx, label in enumerate(labels)}


def save_json(path: str, payload: Dict) -> None:
    """Persist a JSON payload with standard formatting."""
    with open(path, "w") as fp:
        json.dump(payload, fp, indent=2)


def ensure_solc(solc_version: str) -> None:
    """Install the required solc version if it is not yet available."""
    installed = {str(ver) for ver in get_installed_solc_versions()}
    if solc_version not in installed:
        install_solc(solc_version)


def raw_transaction_bytes(signed_txn) -> bytes:
    """Return the raw transaction bytes compatible with web3 v5/v7."""
    if hasattr(signed_txn, "rawTransaction"):
        return signed_txn.rawTransaction
    if hasattr(signed_txn, "raw_transaction"):
        return signed_txn.raw_transaction
    raise AttributeError("SignedTransaction missing raw transaction payload")


def update_status(paths: Dict[str, str], step: str, message: str, *, error: Optional[str] = None) -> None:
    """Store the latest pipeline status for a task."""
    status = {
        "step": step,
        "message": message,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_json(paths["status"], status)


def format_pub_inputs(proof_payload: Dict) -> Dict[str, List[str]]:
    """Convert felt instances to big-endian strings for contract submission."""
    formatted = [
        ezkl.felt_to_big_endian(felt)
        for instance in proof_payload["instances"]
        for felt in instance
    ]
    pretty = "[" + ", ".join(f'"{val}"' for val in formatted) + "]"
    return {"list": formatted, "pretty": pretty}


def compile_verifier_bytecode(sol_path: str, solc_version: str) -> str:
    """Compile the generated verifier contract and return bytecode."""
    if not os.path.isfile(sol_path):
        raise FileNotFoundError(f"Verifier source not found at {sol_path}")
    ensure_solc(solc_version)
    source_name = os.path.basename(sol_path)
    with open(sol_path, "r") as fp:
        source = fp.read()
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {source_name: {"content": source}},
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {"*": {"*": ["evm.bytecode"]}},
            },
        },
        solc_version=solc_version,
    )
    contract_map = compiled["contracts"].get(source_name)
    if not contract_map:
        raise RuntimeError("Compilation output missing contract data")
    contract_name = next(iter(contract_map))
    bytecode = contract_map[contract_name]["evm"]["bytecode"]["object"]
    if not bytecode:
        raise RuntimeError("Verifier bytecode is empty")
    return bytecode


def deploy_verifier_contract(task_id: str) -> Optional[Dict[str, str]]:
    """Deploy the compiled verifier contract and return its metadata."""
    if not (WEB3_HTTP_PROVIDER and WEB3_OPERATOR_KEY):
        return None
    if Web3 is None:
        raise RuntimeError("web3.py is required to deploy the verifier")

    paths = task_paths(task_id)
    sol_path = paths["verifier_sol"]
    abi_path = paths["verifier_abi"]

    if not os.path.isfile(sol_path):
        raise FileNotFoundError(f"Verifier source not found at {sol_path}")
    if not os.path.isfile(abi_path):
        raise FileNotFoundError(f"Verifier ABI not found at {abi_path}")

    bytecode = compile_verifier_bytecode(sol_path, SOLC_VERSION)
    with open(abi_path, "r") as fp:
        abi = json.load(fp)

    web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
    account = web3.eth.account.from_key(WEB3_OPERATOR_KEY)
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    txn = contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "gas": 3_500_000,
            "maxFeePerGas": web3.to_wei("30", "gwei"),
            "maxPriorityFeePerGas": web3.to_wei("2", "gwei"),
            "chainId": web3.eth.chain_id,
        }
    )

    signed = account.sign_transaction(txn)
    tx_hash = web3.eth.send_raw_transaction(raw_transaction_bytes(signed))
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError("Verifier deployment failed")

    return {
        "address": receipt.contractAddress,
        "tx_hash": receipt.transactionHash.hex(),
    }


def extract_prediction(witness_path: str) -> Dict[str, object]:
    """Read witness outputs and return scores plus predicted argmax index."""
    with open(witness_path, "r") as fp:
        payload = json.load(fp)
    outputs = payload.get("pretty_elements", {}).get("rescaled_outputs")
    if not outputs:
        return {"scores": [], "predicted_index": None}
    scores = [float(x) for x in outputs[0]]
    predicted_index = int(np.argmax(scores))
    return {"scores": scores, "predicted_index": predicted_index}


def register_model_onchain(
    task_id: str,
    model_path: str,
    proof_payload: Dict,
    verifier_address: Optional[str],
    accuracy: Optional[float],
) -> Optional[str]:
    """Register the deployed verifier contract and proof metadata on-chain."""
    if not (GENERAL_CONTRACT_ADDRESS and WEB3_HTTP_PROVIDER and WEB3_OPERATOR_KEY and verifier_address):
        return None
    if Web3 is None:
        raise RuntimeError("web3.py is required to register the model on-chain")

    web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
    account = web3.eth.account.from_key(WEB3_OPERATOR_KEY)

    if not os.path.isfile(GENERAL_CONTRACT_ABI_PATH):
        raise FileNotFoundError(f"Contract ABI not found at {GENERAL_CONTRACT_ABI_PATH}")
    with open(GENERAL_CONTRACT_ABI_PATH, "r") as fp:
        abi = json.load(fp)
    contract = web3.eth.contract(address=Web3.to_checksum_address(GENERAL_CONTRACT_ADDRESS), abi=abi)

    with open(model_path, "rb") as fp:
        model_bytes = fp.read()
    model_hash = hashlib.sha256(model_bytes).digest()

    proof_field = proof_payload.get("proof")
    if proof_field is None:
        raise ValueError("Proof payload missing 'proof' field")
    try:
        proof_bytes = HexBytes(proof_field)
    except Exception:
        proof_bytes = json.dumps(proof_field).encode()

    accuracy_scaled = int(round((accuracy or 0.0) * 1_000_000))

    try:
        registry_fn = contract.get_function_by_name(REGISTRY_FUNCTION_NAME)
    except ValueError as exc:
        raise RuntimeError(
            f"Function '{REGISTRY_FUNCTION_NAME}' not found in registry ABI"
        ) from exc

    txn = registry_fn(
        task_id,
        model_hash,
        Web3.to_checksum_address(verifier_address),
        proof_bytes,
        accuracy_scaled,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "gas": 2_000_000,
            "maxFeePerGas": web3.to_wei("30", "gwei"),
            "maxPriorityFeePerGas": web3.to_wei("2", "gwei"),
            "chainId": web3.eth.chain_id,
        }
    )

    signed = account.sign_transaction(txn)
    tx_hash = web3.eth.send_raw_transaction(raw_transaction_bytes(signed))
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError("Contract transaction failed")
    return receipt.transactionHash.hex()


# ------------------------------ pipeline ----------------------------------

async def run_pipeline_async(task_id: str, model_stream) -> Dict[str, object]:
    """Execute the EZKL flow for a single model upload and return summary metadata."""
    paths = task_paths(task_id)
    update_status(paths, "started", "Storing model")

    with open(paths["model"], "wb") as fp:
        fp.write(model_stream.read())

    update_status(paths, "input", "Preparing validation input")
    validation_df = load_validation_dataframe()
    label_index_map = build_label_index_map(validation_df)
    input_vector, target_label = pick_validation_sample(validation_df)
    target_index = label_index_map.get(target_label)
    save_json(paths["input"], {"input_data": input_vector.tolist(), "label": target_label})

    update_status(paths, "settings", "Generating settings")
    py_args = ezkl.PyRunArgs()
    py_args.input_visibility = "private"
    py_args.output_visibility = "public"
    py_args.param_visibility = "fixed"
    ezkl.gen_settings(paths["model"], paths["settings"], py_run_args=py_args)

    update_status(paths, "calibration", "Building calibration set")
    cal_vectors = validation_df.iloc[:, :-1].sample(
        n=min(CALIBRATION_SAMPLES, len(validation_df)), random_state=42
    ).values.astype(float)
    save_json(paths["calibration"], {"input_data": cal_vectors.tolist()})

    update_status(paths, "calibration", "Running ezkl.calibrate_settings")
    ezkl.calibrate_settings(
        data=paths["calibration"],
        model=paths["model"],
        settings=paths["settings"],
        target="resources",
        max_logrows=15,
        scales=[2],
    )

    update_status(paths, "compile", "Compiling circuit")
    ezkl.compile_circuit(paths["model"], paths["compiled"], paths["settings"])

    update_status(paths, "srs", "Fetching SRS")
    await ezkl.get_srs(settings_path=paths["settings"], srs_path=paths["srs"])

    update_status(paths, "witness", "Generating witness")
    ezkl.gen_witness(paths["input"], paths["compiled"], paths["witness"])

    update_status(paths, "setup", "Running setup")
    ezkl.setup(paths["compiled"], paths["vk"], paths["pk"])

    update_status(paths, "prove", "Generating proof")
    proof = ezkl.prove(paths["witness"], paths["compiled"], paths["pk"], paths["proof"])
    if not isinstance(proof, dict):
        with open(paths["proof"], "r") as fp:
            proof = json.load(fp)

    update_status(paths, "verify", "Verifying proof")
    verification_result = ezkl.verify(paths["proof"], paths["settings"], paths["vk"])

    update_status(paths, "verifier", "Exporting EVM verifier")
    await ezkl.create_evm_verifier(
        vk_path=paths["vk"],
        srs_path=paths["srs"],
        settings_path=paths["settings"],
        sol_code_path=paths["verifier_sol"],
        abi_path=paths["verifier_abi"]
    )

    verifier_address = None
    verifier_deploy_tx = None
    if WEB3_HTTP_PROVIDER and WEB3_OPERATOR_KEY:
        update_status(paths, "verifier_deploy", "Deploying verifier contract")
        deployment = deploy_verifier_contract(task_id)
        if deployment:
            verifier_address = deployment["address"]
            verifier_deploy_tx = deployment["tx_hash"]

    pub_inputs = format_pub_inputs(proof)
    prediction = extract_prediction(paths["witness"])
    accuracy = None
    predicted_index = prediction.get("predicted_index")
    if target_index is not None and predicted_index is not None:
        accuracy = 1.0 if predicted_index == target_index else 0.0

    if verifier_address:
        update_status(paths, "register", "Registering model on-chain")
        tx_hash = register_model_onchain(task_id, paths["model"], proof, verifier_address, accuracy)
    else:
        update_status(paths, "register", "Skipping on-chain registration (no verifier deployment)" )
        tx_hash = None

    update_status(paths, "complete", "Pipeline finished")

    return {
        "task_id": task_id,
        "artifacts": paths,
        "pub_inputs_pretty": pub_inputs["pretty"],
        "pub_inputs": pub_inputs["list"],
        "prediction": prediction,
        "verification": verification_result,
        "accuracy": accuracy,
        "verifier_contract": verifier_address,
        "verifier_deploy_tx": verifier_deploy_tx,
        "tx_hash": tx_hash,
    }


def run_pipeline(task_id: str, model_stream) -> Dict[str, object]:
    """Synchronous wrapper so Flask handlers can call the async pipeline."""
    coro = run_pipeline_async(task_id, model_stream)
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:
        if "asyncio.run()" not in str(exc):
            raise
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return loop.run_until_complete(coro)


# ------------------------------- routes -----------------------------------

@app.post("/models")
def post_model():
    task_id = request.form.get("task_id")
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400

    if "model" not in request.files:
        return jsonify({"error": "model (ONNX) file is required"}), 400

    model_file = request.files["model"]
    try:
        result = run_pipeline(task_id, model_file.stream)
    except Exception as exc:  # pragma: no cover - runtime logging
        paths = task_paths(task_id)
        update_status(paths, "failed", "Pipeline error", error=str(exc))
        return jsonify({"error": str(exc)}), 500

    return jsonify(result), 201


@app.get("/models/<task_id>/status")
def get_status(task_id: str):
    paths = task_paths(task_id)
    if not os.path.isfile(paths["status"]):
        return jsonify({"error": "unknown task id"}), 404
    with open(paths["status"], "r") as fp:
        status = json.load(fp)
    return jsonify(status)


@app.get("/models/<task_id>/artifacts/<artifact>")
def get_artifact(task_id: str, artifact: str):
    paths = task_paths(task_id)
    candidate = os.path.join(paths["base"], artifact)
    if not os.path.isfile(candidate):
        return jsonify({"error": "artifact not found"}), 404
    with open(candidate, "rb") as fp:
        data = fp.read()
    return app.response_class(data, mimetype="application/octet-stream")


if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))