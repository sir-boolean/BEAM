import requests
import json
import time
from datetime import datetime
import base58
import asyncio
import aiohttp
from collections import defaultdict
import os

# Configuration
HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_DELAY = 1  # Delay in seconds between eth_getLogs calls
MAX_CONCURRENT_REQUESTS = 5  # Maximum number of concurrent API requests

# Cache for transaction receipts
tx_receipt_cache = {}

async def get_latest_block(session, url):
    """Retrieves the latest block number from the blockchain."""
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    async with session.post(url, headers=HEADERS, json=payload) as response:
        result = await response.json()
        return int(result["result"], 16)

async def get_logs(session, url, from_block, to_block, topics):
    """Retrieves logs from the blockchain with rate limiting."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{"fromBlock": hex(from_block), "toBlock": to_block, "topics": topics}],
        "id": 1,
    }
    async with session.post(url, headers=HEADERS, json=payload) as response:
        result = await response.json()
        await asyncio.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        return result.get("result", [])

async def get_transaction_receipt(session, url, tx_hash):
    """Retrieves the transaction receipt for a given transaction hash with caching."""
    if tx_hash in tx_receipt_cache:
        return tx_receipt_cache[tx_hash]
    
    payload = {"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx_hash], "id": 1}
    async with session.post(url, headers=HEADERS, json=payload) as response:
        result = await response.json()
        receipt = result.get("result")
        if receipt:
            tx_receipt_cache[tx_hash] = receipt
        return receipt

def log_message(log_file, message):
    """Logs a message to the console and a log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(log_file, "a") as f:
        f.write(full_message + "\n")

async def get_validation_id(session, url, node_id):
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
    validators_url = url.replace("/rpc", "/validators")
    async with session.post(validators_url, headers=HEADERS, json=payload) as response:
        result = await response.json()
        validators_dict = result.get("result", {})
        validators_list = validators_dict.get("validators", [])

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
    except Exception as e:
        return f"Error: Invalid Base58 string or conversion failed. Details: {str(e)}"

async def process_node_delegations(session, url, validation_id_hex, log_file, report_file):
    """Processes node delegations and generates a report."""
    processed_txs = set()
    node_delegations = []

    log_message(log_file, "Processing node delegations...")
    latest_block = await get_latest_block(session, url)
    logs = await get_logs(session, url, 0, "latest", [None, None, validation_id_hex])

    # Track unique token IDs to prevent double counting
    processed_token_ids = set()
    
    # Process logs sequentially to ensure accurate counting
    for log in logs:
        tx_hash = log["transactionHash"]
        if tx_hash not in processed_txs:
            receipt = await get_transaction_receipt(session, url, tx_hash)
            if receipt:
                wallet = None
                token_ids = []
                
                # First pass: find the wallet address
                for log_entry in receipt["logs"]:
                    topics = log_entry.get("topics", [])
                    if not topics:
                        continue
                    
                    if topics[0] == "0xdf91f7709a30fda3fc5fc5dc97cb5d5b05e67e193dccaaef3cb332d23fda83d1" and len(topics) > 3:
                        wallet = topics[3][-40:]
                        break
                
                # Second pass: collect token IDs
                if wallet:
                    for log_entry in receipt["logs"]:
                        topics = log_entry.get("topics", [])
                        if not topics:
                            continue
                        
                        if topics[0] == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef" and len(topics) > 3:
                            try:
                                token_id = int(topics[3], 16)
                                # Only add if we haven't seen this token ID before
                                token_id_key = (wallet, token_id)
                                if token_id_key not in processed_token_ids:
                                    token_ids.append(token_id)
                                    processed_token_ids.add(token_id_key)
                            except ValueError:
                                log_message(log_file, f"Warning: Invalid token ID format in tx {tx_hash}")
                
                if wallet and token_ids:
                    for token_id in token_ids:
                        node_delegations.append((tx_hash, wallet, token_id))
                        log_message(log_file, f"Node delegation - Transaction: {tx_hash}, Wallet: 0x{wallet}, Token ID: {token_id}")
            
            processed_txs.add(tx_hash)

    generate_node_delegation_report(node_delegations, log_file, f"{os.path.splitext(report_file)[0]}_delegations.json")
    log_message(log_file, f"Node delegation processing complete. Last block: {latest_block}.")

def generate_node_delegation_report(node_delegations, log_file, report_file):
    """Generates a report for node delegations."""
    node_data = defaultdict(list)
    for tx_hash, wallet, token_id in node_delegations:
        if wallet:
            node_data[wallet].append(str(token_id))

    report = {"nodes_per_wallet": [], "total_nodes": 0}
    for wallet, token_ids in node_data.items():
        entry = {"wallet": f"0x{wallet}", "nodes": token_ids, "total_nodes": len(token_ids)}
        report["nodes_per_wallet"].append(entry)
        report["total_nodes"] += len(token_ids)

    log_message(log_file, "Node Delegations Report:")
    for entry in report["nodes_per_wallet"]:
        log_message(log_file, f"Wallet: {entry['wallet']}")
        log_message(log_file, f"Nodes: {', '.join(entry['nodes'])}")
        log_message(log_file, f"Total Nodes: {entry['total_nodes']}")
        log_message(log_file, "---")
    log_message(log_file, f"Total Nodes (all wallets): {report['total_nodes']}")

    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
    log_message(log_file, f"Report saved to: {report_file}")

async def process_beam_stakes(session, url, validation_id_hex, validator_stake, log_file, report_file):
    """Processes BEAM stakes and generates a report."""
    processed_txs = set()
    beam_stakes = []

    log_message(log_file, "Processing BEAM stakes...")
    latest_block = await get_latest_block(session, url)
    logs = await get_logs(session, url, 0, "latest", [None, None, validation_id_hex])

    # Process logs in batches to control concurrency
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def process_log(log):
        async with semaphore:
            tx_hash = log["transactionHash"]
            if tx_hash not in processed_txs:
                receipt = await get_transaction_receipt(session, url, tx_hash)
                if receipt:
                    wallet, amount = None, 0
                    stake_event_found = False
                    
                    for log_entry in receipt["logs"]:
                        topics = log_entry.get("topics", [])
                        if not topics:
                            continue
                            
                        if topics[0] == "0x6e350dd49b060d87f297206fd309234ed43156d890ced0f139ecf704310481d3":
                            stake_event_found = True
                            
                    if stake_event_found:
                        for log_entry in receipt["logs"]:
                            topics = log_entry.get("topics", [])
                            if not topics:
                                continue
                                
                            if topics[0] == "0xdf91f7709a30fda3fc5fc5dc97cb5d5b05e67e193dccaaef3cb332d23fda83d1" and len(topics) > 3:
                                wallet = topics[3][-40:]
                                data = log_entry.get("data", "")
                                
                                # More robust data parsing
                                try:
                                    if len(data) >= 194:
                                        amount = int(data[130:194], 16)
                                    elif len(data) >= 66:  # Try alternative parsing if standard format doesn't match
                                        amount = int(data[2:66], 16)
                                except ValueError:
                                    log_message(log_file, f"Warning: Invalid amount format in tx {tx_hash}")
                                    
                        if wallet and amount > 0:
                            beam_stakes.append((tx_hash, wallet, amount))
                            log_message(log_file, f"BEAM stake - Transaction: {tx_hash}, Wallet: 0x{wallet}, BEAM: {amount}")
                processed_txs.add(tx_hash)
                return True
            return False
    
    # Process logs concurrently
    tasks = [process_log(log) for log in logs]
    await asyncio.gather(*tasks)

    generate_beam_stake_report(beam_stakes, validator_stake, log_file, f"{os.path.splitext(report_file)[0]}_stakes.json")
    log_message(log_file, f"BEAM stake processing complete. Last block: {latest_block}.")

def generate_beam_stake_report(beam_stakes, validator_stake, log_file, report_file):
    """Generates a report for BEAM stakes."""
    stake_data = defaultdict(list)
    for tx_hash, wallet, amount in beam_stakes:
        stake_data[wallet].append({"transaction": tx_hash, "amount": amount})

    report = {"stakes_per_wallet": [], "validator_stake": validator_stake, "total_beam": 0}
    for wallet, stakes in stake_data.items():
        total = sum(stake["amount"] for stake in stakes)
        entry = {"wallet": f"0x{wallet}", "stakes": stakes, "total_beam": total}
        report["stakes_per_wallet"].append(entry)
        report["total_beam"] += total
    report["total_beam"] += validator_stake

    log_message(log_file, "BEAM Stakes Report:")
    for entry in report["stakes_per_wallet"]:
        log_message(log_file, f"Wallet: {entry['wallet']}")
        for stake in entry["stakes"]:
            log_message(log_file, f"Transaction: {stake['transaction']}, BEAM: {stake['amount']}")
        log_message(log_file, f"Total BEAM: {entry['total_beam']}")
        log_message(log_file, "---")
    log_message(log_file, f"Validator Stake: {validator_stake} BEAM")
    log_message(log_file, f"Total BEAM (including validator): {report['total_beam']}")

    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
    log_message(log_file, f"Report saved to: {report_file}")

async def main():
    ip_address = input("Enter the IP address (default: localhost): ") or "localhost"
    port = input("Enter the port number (default: 9650): ") or "9650"
    url = f"http://{ip_address}:{port}/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/rpc"
    node_id_input = input("Enter your Node-ID: ")
    node_id = node_id_input.replace("NodeID-", "")
    log_file = f"{node_id}_validator_report.log"
    report_file = f"{node_id}_validator_report.json"

    # Clear previous log file
    with open(log_file, "w") as f:
        f.write("")  # Create or clear the log file

    async with aiohttp.ClientSession() as session:
        validation_id = await get_validation_id(session, url, node_id_input)

        if validation_id:
            validation_id_hex = convert_validation_id(validation_id)
            if not validation_id_hex.startswith("Error"):
                choice = input("Process node delegations (d), BEAM stakes (s), or both (b)? [d/s/b]: ").lower()

                validator_stake = 0
                if choice in ["s", "b"]:
                    try:
                        validator_stake = int(input("Enter validator's BEAM stake (0 if not applicable): "))
                    except ValueError:
                        log_message(log_file, "Invalid stake amount, using 0 as default.")
                        validator_stake = 0

                tasks = []
                if choice in ["d", "b"]:
                    tasks.append(process_node_delegations(session, url, validation_id_hex, log_file, report_file))
                if choice in ["s", "b"]:
                    tasks.append(process_beam_stakes(session, url, validation_id_hex, validator_stake, log_file, report_file))
                
                await asyncio.gather(*tasks)
            else:
                log_message(log_file, validation_id_hex)
        else:
            log_message(log_file, "Node-ID not found.")

if __name__ == "__main__":
    asyncio.run(main())
