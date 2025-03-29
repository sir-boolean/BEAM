# Validator Analytics Script

This script has been inspired by Jesucripto13's work, which you can find here: https://github.com/Jesucripto13/beam-validator-reports.

It retrieves and processes validator data from BEAM L1 subnet on AVAX, including node delegations and BEAM stakes. This optimized version ensures accurate counting while improving performance.

## Key Features

- **Accurate Node Delegation Counting**: Uses sequential processing with unique token tracking
- **Asynchronous Processing**: Leverages asyncio and aiohttp for non-blocking API requests
- **Performance Optimizations**: Maintains transaction receipt cache to reduce redundant calls
- **Improved Error Handling**: Better validation and edge case management
- **Organized Output**: Separate report files for different data types

## Prerequisites

* **Python 3.x:** Ensure you have Python 3 installed on your system.
* **BEAM L1 subnet:** This script assumes you insert Node-ID for a running validator.
* **Python Libraries:** Install the required libraries using pip:
    ```bash
    pip install requests base58 asyncio aiohttp
    ```

## Configuration

1. **Network URL:** The script prompts you for the IP address and port. If you want to use the default values (localhost:9650), just press Enter.
2. **Subnet ID:** The subnet ID is hardcoded in the script. If you need to change it, modify the URL in the `main` function:
    ```python
    url = f"http://{ip_address}:{port}/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/rpc"
    ```
    Change the `2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn` to your subnet ID.
3. **Rate Limiting:** You can adjust `RATE_LIMIT_DELAY` and `MAX_CONCURRENT_REQUESTS` at the top of the script to optimize for your environment.
4. **Output Files:** The script creates separate files for logs and reports:
   - `[Node-ID]_validator_report.log` - Detailed execution log
   - `[Node-ID]_validator_report_delegations.json` - Node delegation report
   - `[Node-ID]_validator_report_stakes.json` - BEAM stakes report

## Usage

1. **Run the Script:**
    ```bash
    python3 validator_analytics.py
    ```
2. **Enter IP Address and Port:** Enter the IP address and port of the Avalanche node, or press Enter for defaults.
3. **Enter Node-ID:** Provide the Node-ID of the validator you want to analyze.
4. **Choose Processing Options:** Select whether to process node delegations, BEAM stakes, or both.
5. **Enter Validator Stake (if applicable):** If processing BEAM stakes, enter the validator's BEAM stake.
6. **View Reports:** Generated reports will be saved in JSON format in the current directory.

## Technical Details

The script uses a two-pass log processing approach for node delegations:
1. First pass identifies the wallet address
2. Second pass collects token IDs associated with the wallet
3. Unique (wallet, token_id) pairs are tracked to prevent double counting

BEAM stake processing utilizes concurrent API requests with a semaphore to control the level of parallelism while maintaining data integrity.

## Delegations

If you would like to delegate your BEAM nodes or BEAM tokens to my validator, I would be very grateful. My validator details are:
* **Validator Name:** sir\_boolean
* **Node-ID:** NodeID-CEsABmctyhhNGQHbPGCRaAyejHEiAD1NU

Your support is highly appreciated!

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues.

## License

This project is licensed under the MIT License.
