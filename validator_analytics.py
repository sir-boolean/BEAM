import requests
import json
import time
from datetime import datetime
import base58

# Configuration
URL = "http://127.0.0.1:9650/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/rpc"
HEADERS = {"Content-Type": "application/json"}
LOG_FILE = "validator_report.log"
REPORT_FILE = "validator_report.json"
RATE_LIMIT_DELAY = 1  # Delay in seconds between eth_getLogs calls

def get_latest_block():
    """Retrieves the latest block number from the blockchain."""
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
    return int(response.json()["result"], 16)

def get_logs(from_block, to_block, topics):
    """Retrieves logs from the blockchain with rate limiting."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{"fromBlock": hex(from_block), "toBlock": to_block, "topics": topics}],
        "id": 1,
    }
    response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
    time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
    return response.json().get("result", [])

def get_transaction_receipt(tx_hash):
    """Retrieves the transaction receipt for a given transaction hash."""
    payload = {"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx_hash], "id": 1}
    response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
    return response.json().get("result")

def log_message(message):
    """Logs a message to the console and a log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a") as f:
        f.write(full_message + "\n")

def get_validation_id(node_id):
    """Retrieves the validationID from the nodeID."""
    if not node_id.startswith("NodeID-"):
        node_id = "NodeID-" + node_id
    payload = {
        "jsonrpc": "2.0",
        "method": "validators.getCurrentValidators",
        "params": {
            "nodeIDs": [node_id]
        },
        "id": 1,
    }
    url = "http://127.0.0.1:9650/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/validators"
    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))

    validators_dict = response.json().get("result", {}) # changed this line
    validators_list = validators_dict.get("validators", []) # added this line

    if validators_list:
        return validators_list[0]["validationID"]
    else:
        return None

def convert_validation_id(validation_id):
    """Converts a Base58 encoded validationID to a hexadecimal string."""
    try:
        decoded = base58.b58decode(validation_id)
        payload = decoded[0:-4].hex()
        return f"0x{payload}"
    except ValueError:
        return "Error: Invalid Base58 string."

def process_node_delegations(validation_id_hex):
    """Processes node delegations and generates a report."""
    processed_txs = set()
    node_delegations = []

    log_message("Processing node delegations...")
    latest_block = get_latest_block()
    logs = get_logs(0, "latest", [None, None, validation_id_hex])

    for log in logs:
        tx_hash = log["transactionHash"]
        if tx_hash not in processed_txs:
            receipt = get_transaction_receipt(tx_hash)
            if receipt:
                wallet = None
                token_ids = []
                for log_entry in receipt["logs"]:
                    if log_entry["topics"][0] == "0xdf91f7709a30fda3fc5fc5dc97cb5d5b05e67e193dccaaef3cb332d23fda83d1":
                        wallet = log_entry["topics"][3][-40:]
                    if log_entry["topics"][0] == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":
                        token_ids.append(int(log_entry["topics"][3], 16))
                if wallet and token_ids:
                    for token_id in token_ids:
                        node_delegations.append((tx_hash, wallet, token_id))
                        log_message(f"Node delegation - Transaction: {tx_hash}, Wallet: 0x{wallet}, Token ID: {token_id}")
            processed_txs.add(tx_hash)

    generate_node_delegation_report(node_delegations)
    log_message(f"Node delegation processing complete. Last block: {latest_block}.")

def generate_node_delegation_report(node_delegations):
    """Generates a report for node delegations."""
    node_data = {}
    for tx_hash, wallet, token_id in node_delegations:
        if wallet:
            node_data.setdefault(wallet, []).append(str(token_id))

    report = {"nodes_per_wallet": [], "total_nodes": 0}
    for wallet, token_ids in node_data.items():
        entry = {"wallet": f"0x{wallet}", "nodes": token_ids, "total_nodes": len(token_ids)}
        report["nodes_per_wallet"].append(entry)
        report["total_nodes"] += len(token_ids)

    log_message("Node Delegations Report:")
    for entry in report["nodes_per_wallet"]:
        log_message(f"Wallet: {entry['wallet']}")
        log_message(f"Nodes: {', '.join(entry['nodes'])}")
        log_message(f"Total Nodes: {entry['total_nodes']}")
        log_message("---")
    log_message(f"Total Nodes (all wallets): {report['total_nodes']}")

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=4)
    log_message(f"Report saved to: {REPORT_FILE}")

def process_beam_stakes(validation_id_hex, validator_stake):
    """Processes BEAM stakes and generates a report."""
    processed_txs = set()
    beam_stakes = []

    log_message("Processing BEAM stakes...")
    latest_block = get_latest_block()
    logs = get_logs(0, "latest", [None, None, validation_id_hex])

    for log in logs:
        tx_hash = log["transactionHash"]
        if tx_hash not in processed_txs:
            receipt = get_transaction_receipt(tx_hash)
            if receipt:
                wallet, amount = None, 0
                if any(log_entry["topics"][0] == "0x6e350dd49b060d87f297206fd309234ed43156d890ced0f139ecf704310481d3" for log_entry in receipt["logs"]):
                    for log_entry in receipt["logs"]:
                        if log_entry["topics"][0] == "0xdf91f7709a30fda3fc5fc5dc97cb5d5b05e67e193dccaaef3cb332d23fda83d1":
                            wallet = log_entry["topics"][3][-40:]
                            if len(log_entry["data"]) >= 194:
                                amount = int(log_entry["data"][130:194], 16)
                    if wallet and amount > 0:
                        beam_stakes.append((tx_hash, wallet, amount))
                        log_message(f"BEAM stake - Transaction: {tx_hash}, Wallet: 0x{wallet}, BEAM: {amount}")
            processed_txs.add(tx_hash)

    generate_beam_stake_report(beam_stakes, validator_stake)
    log_message(f"BEAM stake processing complete. Last block: {latest_block}.")

def generate_beam_stake_report(beam_stakes, validator_stake):
    """Generates a report for BEAM stakes."""
    stake_data = {}
    for tx_hash, wallet, amount in beam_stakes:
        stake_data.setdefault(wallet, []).append({"transaction": tx_hash, "amount": amount})

    report = {"stakes_per_wallet": [], "validator_stake": validator_stake, "total_beam": 0}
    for wallet, stakes in stake_data.items():
        total = sum(stake["amount"] for stake in stakes)
        entry = {"wallet": f"0x{wallet}", "stakes": stakes, "total_beam": total}
        report["stakes_per_wallet"].append(entry)
        report["total_beam"] += total
    report["total_beam"] += validator_stake

    log_message("BEAM Stakes Report:")
    for entry in report["stakes_per_wallet"]:
        log_message(f"Wallet: {entry['wallet']}")
        for stake in entry["stakes"]:
            log_message(f"Transaction: {stake['transaction']}, BEAM: {stake['amount']}")
        log_message(f"Total BEAM: {entry['total_beam']}")
        log_message("---")
    log_message(f"Validator Stake: {validator_stake} BEAM")
    log_message(f"Total BEAM (including validator): {report['total_beam']}")

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=4)
    log_message(f"Report saved to: {REPORT_FILE}")

# Main
node_id = input("Enter your Node-ID: ")
validation_id = get_validation_id(node_id)

if validation_id:
    validation_id_hex = convert_validation_id(validation_id)
    if not validation_id_hex.startswith("Error"):
        choice = input("Process node delegations (d), BEAM stakes (s), or both (b)? [d/s/b]: ").lower()
        if choice in ["d", "b"]:
            process_node_delegations(validation_id_hex)
        if choice in ["s", "b"]:
            validator_stake = int(input("Enter validator's BEAM stake (0 if not applicable): "))
            process_beam_stakes(validation_id_hex, validator_stake)
    else:
        log_message(validation_id_hex)
else:
    log_message("Node-ID not found.")
