# EmetEventExtractor
This script retrieves EMET triggered mitigations using BAM functions, stores them, deduplicates them, and writes them to a file. The file can then be ingested using Splunk's Universal Forwarder.

## Cool Features

####Configuration Files
This script depends on a config file formatted in JSON. Customizable settings include: Username, Password, Server, Filters, Returns, Log Filepath, and Output Filepath. 
####LOGS
The script also documents its activity using logs. It will create a file and update the process of the program in each function. This should help largely with debugging. Logs will be erased from the file if they are over 7 days old.
