## Intel-Generator

This repo contains some artificats & programs to create fake intelligence reports, index them into Elasticsearch, and query them using a Retrieval Augmented Generation demo app.

This repo contains:
- `intel-generator.py`, a script that will generate a bunch of fake intelligence reports and upload them to Elasticsearch for analysis.
- `genai-intel-demo.py`, a Retrieval Augmented Generation (RAG) demo frontend to query the fake intel reports.

### Quickstart
1. Clone this repo
2. Ensure dependencies are installed:
```
pip3 install -r requirements.txt
```

4. Make a copy of `config.toml`, rename it to something memorable, and fill in the required settings:
```
- NUM_REPORTS = number of fake reports to generate

- ELASTIC_CLOUD_ID = Elastic cloud ID to send output to
- ELASTIC_USER = Elasticsearch username to use
- ELASTIC_PASSWORD = Elasticsearch password to use
- ELASTIC_INDEX = index name to use (recommend "intel-reports")

- AZURE_OPENAI_API_KEY = Azure OpenAI key
- AZURE_API_VERSION = Azure OpenAI API version (recommend "2024-02-01")
- AZURE_ENDPOINT = Azure OpenAI endpoint URL
- AZURE_DEPLOYMENT = Azure OpenAI deployment name
- AZURE_MODEL = Azure OpenAI model to use

- LOCAL_LLM_URL = URL of self-hosted LLM to use (e.g. http://1.2.3.4:1234/v1)
- LOCAL_LLM_API_KEY = self-hosted LLM API key (if security is not enabled, this can be anything)
- LOCAL_LLM_MODEL = self-hosted model to use (e.g. mixtral)
```
4. Run the `intel-generator.py` script and substitute in your custom `config.toml` at runtime:
```
python3 intel-generator.py --config pathoge-config.toml
```

5. To start the web UI frontend run the following command and substitute in your custom `config.toml`.
```
streamlit run genai-intel-demo.py -- --config config-pathoge.toml
```

If utilizing a self-hosted LLM, add the flag `--local-llm`:
```
streamlit run genai-intel-demo.py -- --config config-pathoge.toml --local-llm
```