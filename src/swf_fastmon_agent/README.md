# Agents for fast monitoring of the ePIC streaming workflow testbed

The agent is designed to pull metadata from Time Frames (TF) and distribute this information via message queues, enabling remote monitoring of the ePIC data acquisition system.

## Current implementation for the test bed 

1. STF files found in the DAQ namespace are processed by the agent to "extract" TFs (currently emulated as the STFs contain only metadata).
2. The agent generates metadata for each TF, and records the information in the monitoring database.
   - The metadata includes:
     - Run ID
     - TF start and end timestamps
     - File name
     - State and substate of the run
     - Additional attributes as needed
3. The agent sends metadata of the TFs to the message queue, allowing remote monitoring of the ePIC data acquisition.

## How to Use

