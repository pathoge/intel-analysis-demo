## Intel-Workshop

A Python program to set up the Intel Analysis Workshop

This script will generate a bunch of fake intelligence reports and upload them to Elasticsearch for analysis.

### Quickstart
1. Clone this repo
2. Ensure dependencies are installed:
```
pip3 install -r requirements.txt
```

4. Make a copy of `config.toml`, rename it to something memorable, and fill in the required settings:
```
- NUM_REPORTS = number of fake reports to generate
- CLOUD_ID = Elastic cloud ID to send output to
- USER = Elasticsearch username to use
- PASSWORD = Elasticsearch password to use
- INDEX = index name to use (recommend 'intel-reports' as future saved objects will be based off that name)
```
4. Run the script, specifying your new `config.toml` at runtime:
```
python3 intel-generator.py --config pathoge-config.toml
```
