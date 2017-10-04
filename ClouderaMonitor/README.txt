README for Cloudera Manager Monitoring Agent

Purpose: Provide an external monitoring system for Cloudera-based Hadoop clusters, particularly for unauthorized configuration changes and other security-relevant monitoring requirements.

Implementation: This utility uses the Cloudera Manager API to extract the configuration of all managed clusters, saves the configuration locally, and on future executions of the utility compares the active configuration to the saved configuration, saving a comparison report to the file 'ConfigReport.json'. If configuration changes are detected, an email alert is also sent.

Usage:
===Ad-Hoc Usage===
1. Execute runClouderaMonitor.py
2. If no previous utility configuration is detected, 
	i. The utility queries you for the following information:
		a. Cloudera Manager information (CM FQDN, port, API user, password, API version number, and whether or not to use TLS). This utility supports tracking the configurations of any number of Cloudera Manager instances
		b. Email alert SMTP information
	ii. Once setup completes, the utility extracts the existing configuration from the CM API for each Cloudera Manager instance configured
3. The utility loads the saved CM configuration into memory, then extracts the current CM configuration, and performs a comparison.
4. A 'ConfigReport.json' file is created with three data nodes: PRIOR CONFIG UNIQUE, CURRENT CONFIG UNIQUE, and CONFIGURATION DIFFERENCES
	a. PRIOR CONFIG UNIQUE includes any configuration items that exist in the previous (saved) configuration which are not in the current configuration just extracted from the CM API. The string "_UNIQUE" is added at the point in the configuration tree where the key is not detected in the current configuration, so every entry under that point in the tree is also unique.
	b. CURRENT CONFIG UNIQUE includes any configuration items that exist in the current (active extract) configuration which are not in the saved configuration. The "_UNIQUE" is added in the same manner to these entries.
	c. CONFIGURATION DIFFERENCES describes any keys that exist in both configurations but have different values between the saved and current configurations.
5. If configuration changes are detected and email alerts were setup, the comparison results are emailed to the configured recipients.

===Scheduled Usage===
Once initial configuration is performed, the utility can be run on a scheduled basis to perform consistent configuration monitoring.