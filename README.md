## Intel Analysis Demo

This repo contains artificats & Python programs to generator completely fake intelligence reports, index them into Elasticsearch, and query them using a Retrieval Augmented Generation (RAG) demo app.

### Quickstart - Docker (recommended)
1. Clone this repo & change directories into the repo folder

2. Build the Docker container:
```
docker build --no-cache -t ia-genai-demo:latest .
```

3. While that's running, make a copy of `config.toml`, rename it to something memorable, and fill out the required settings (note - you can choose Azure or Local LLM):
```
NUM_REPORTS = number of fake reports to generate

ELASTIC_CLOUD_ID = Elastic cloud ID to send output to
ELASTIC_API_KEY = Elasticseach API key to use (optional if using username/password)
ELASTIC_USER = Elasticsearch username to use (optional if using api key)
ELASTIC_PASSWORD = Elasticsearch password to use (optional if using api key)
ELASTIC_INDEX = index name to use (recommend "intel-reports")

AZURE_OPENAI_API_KEY = Azure OpenAI key
AZURE_API_VERSION = Azure OpenAI API version (e.g. "2024-02-01")
AZURE_ENDPOINT = Azure OpenAI endpoint URL
AZURE_DEPLOYMENT = Azure OpenAI deployment name
AZURE_MODEL = Azure OpenAI model to use

LOCAL_LLM = "true"
LOCAL_LLM_URL = URL of self-hosted LLM to use (e.g. http://1.2.3.4:1234/v1)
LOCAL_LLM_API_KEY = self-hosted LLM API key (if security is not enabled, this can be anything)
LOCAL_LLM_MODEL = self-hosted model to use (e.g. mixtral)
```

4. Run the container and pass in your `config.toml` at runtime:
```
docker run --rm -v ./config-pathoge.toml:/app/config.toml --name ia-genai-demo -p 8501:8501 ia-genai-demo:latest
```
NOTE: On Windows you may have to run a slightly modified command:
```
docker run --rm -v //$(PWD)/config-pathoge.toml:/app/config.toml --name ia-genai-demo -p 8501:8501 ia-genai-demo:latest
```

5. Navigate to http://localhost:8501 in your favorite web browser.

6. (Initial run) In the sidebar of the web app, check the "Data setup" box and click the button to generate the intelligence reports and send them to your Elasticsearch cluster. WARNING: this action deletes the index if it already exists. It also requires the Elasticsearch cluster to have the ELSER v2 model already deployed and running with the name `.elser_model_2`. 

### Quickstart - Bare Python
1. Clone this repo

2. Ensure dependencies are installed:
```
pip3 install -r requirements.txt
```

3. See step 3 above. 

4. To start the application, run the following command and substitute in your custom `config.toml`.
```
streamlit run genai-intel-demo.py -- --config config-pathoge.toml
```

5. See step 5 above.

6. See step 6 above.