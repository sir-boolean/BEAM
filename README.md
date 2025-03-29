# Validator Analytics Script
test
This script has been inspired by Jesucripto13 work, you can find it here: https://github.com/Jesucripto13/beam-validator-reports.
Ii retrieves and processes validators data, including node delegations and BEAM stakes, from BEAM L1 subnet on AVAX. It's designed to help you analyze validator activity and generate reports.

## Prerequisites

* **Python 3.x:** Ensure you have Python 3 installed on your system.
* **BEAM L1 subnet:** This script assumes you insert Node-ID for a running validator.
* **Python Libraries:** Install the required libraries using pip:

    ```bash
    pip install requests base58
    ```

## Configuration

1.  **Network URL:** If you want you can modify the `URL` variable in the script to match your subnet in the Avalanche network.
2.  **Subnet ID:** The subnet ID is hardcoded in the script, if you need to change it please modify the following line in the `get_validation_id` function:
    ```python
    url = "[http://127.0.0.1:9650/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/validators](http://127.0.0.1:9650/ext/bc/2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn/validators)"
    ```
    Change the `2tmrrBo1Lgt1mzzvPSFt73kkQKFas5d1AP88tv9cicwoFp8BSn` to your subnet ID.
3.  **Log and Report Files:** The script creates `validator_report.log` and `validator_report.json` files in the same directory. You can change these file names by modifying the `LOG_FILE` and `REPORT_FILE` variables in the script.

## Usage

1.  **Run the Script:**

    ```bash
    python3 validator_analytics.py
    ```

2.  **Enter Node-ID:** The script will prompt you to enter the Node-ID of the validator you want to analyze.
3.  **Choose Processing Options:** The script will ask you to choose whether to process node delegations, BEAM stakes, or both.
4.  **Enter Validator Stake (if applicable):** If you choose to process BEAM stakes, you'll be prompted to enter the validator's BEAM stake.
5.  **View Reports:** The script will generate a report in `validator_report.json` and log messages in `validator_report.log`.

## Script Functionality

* **`get_validation_id(node_id)`:** Retrieves the validationID from the provided Node-ID.
* **`convert_validation_id(validation_id)`:** Converts the validationID from Base58 to hexadecimal format.
* **`process_node_delegations(validation_id_hex)`:** Processes node delegations and generates a report.
* **`process_beam_stakes(validation_id_hex, validator_stake)`:** Processes BEAM stakes and generates a report.
* **`generate_node_delegation_report(node_delegations)`:** Generates a JSON report for node delegations.
* **`generate_beam_stake_report(beam_stakes, validator_stake)`:** Generates a JSON report for BEAM stakes.

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues.

## License

This project is licensed under the MIT License.
