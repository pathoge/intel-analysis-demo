import argparse
import json
import logging
import random
import time
import tomllib
from datetime import datetime, timedelta
import uuid

import streamlit as st
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk, BulkIndexError
from openai import AzureOpenAI, OpenAI


logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)

today = datetime.today().strftime("%A, %B %d, %Y")

st.set_page_config(page_title="GenAI-Powered Intelligence Analysis", page_icon="🔍")

with open("./.streamlit/style.html", "r") as f:
  style = f.read()
  
st.markdown(style, unsafe_allow_html=True)


def connect_open_ai(api_key: str, api_version: str, endpoint: str, deployment: str) -> AzureOpenAI:
    open_ai_client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint,
        azure_deployment=deployment,
    )
    return open_ai_client


def connect_self_hosted_llm(base_url: str, api_key: str) -> OpenAI:
    open_ai_client = OpenAI(
        base_url=config["LOCAL_LLM_URL"], 
        api_key=config["LOCAL_LLM_API_KEY"]
    )
    return open_ai_client


def connect_es(config: dict) -> Elasticsearch:
    if "ELASTIC_API_KEY" in config:
        try:
            client = Elasticsearch(
                cloud_id=config["ELASTIC_CLOUD_ID"],
                api_key=config["ELASTIC_API_KEY"]
            )
            # Test the connection
            client.info()
            return client
        except Exception:
            pass
    if "ELASTIC_USER" in config and "ELASTIC_PASSWORD" in config:
        try:
            client = Elasticsearch(
                cloud_id=config["ELASTIC_CLOUD_ID"],
                basic_auth=(config["ELASTIC_USER"], config["ELASTIC_PASSWORD"])
            )
            # Test the connection
            client.info()
            return client
        except Exception:
            pass 
    raise Exception("Failed to connect to Elasticsearch with provided credentials.")


def setup_es(es, reset):
    if reset and es.indices.exists(index=config["ELASTIC_INDEX"]):
        logging.info("Deleting existing index")
        es.indices.delete(index=config["ELASTIC_INDEX"])

    if not es.indices.exists(index=config["ELASTIC_INDEX"]):
        logging.info("Creating index")
        mapping = {
            # "_source": {
            #     "excludes": [
            #         "details_embeddings"
            #     ]
            # },
            "properties": {
                "classification": {"type": "keyword"},
                "compartments": {"type": "keyword"},
                "date": {"type": "date"},
                "details": {"type": "text"},
                "details_embeddings": {"type": "sparse_vector"},
                "report_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "group": {"type": "keyword"},
                "summary": {"type": "text"},
                "country.name": {"type": "keyword"},
                "country.coordinates": {"type": "geo_point"},
                "country.code": {"type": "keyword"},
            }
        }
        settings = {
            "index": {
                # "number_of_shards": "2",
                # "number_of_replicas": "0",
                # "refresh_interval": "-1",
                "default_pipeline": "intel-workshop"
            }
        }
        es.indices.create(index=config["ELASTIC_INDEX"], mappings=mapping, settings=settings)

    logging.info("Creating/updating ingest pipeline")
    processors = [
        {
            "inference": {
                "model_id": ".elser_model_2_linux-x86_64",
                "input_output": [
                    {
                        "input_field": "details",
                        "output_field": "details_embeddings"
                    }
                ]
            }
        }
    ]
    es.ingest.put_pipeline(id="intel-workshop", processors=processors)
    return True


def read_config(config_path: str) -> dict:
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


def read_file(file_name):
    with open(file_name, "r") as file:
        data = json.load(file)
    return data


def generate_selector():
    return str(uuid.uuid4())

def bulk_ingest(es, index, docs):
    x = 0
    progress_bar = st.sidebar.progress(0, text="Working...")
    try:
        logging.info("Sending docs to ES")
        for ok, action in streaming_bulk(
            client=es, index=index, actions=yield_doc(docs), chunk_size=10
        ):
            if ok:
                x += 1
                progress_bar.progress(x / len(docs), text=f"Ingested {x} documents...")
            else:
                logging.error(f"{ok} {action}")
        return True, None
    except BulkIndexError as e:
        print(f"{len(e.errors)} document(s) failed to index.")
        for error in e.errors:
            print(error)
        return False, e.errors[0]


def yield_doc(docs):
    for doc in docs:
        yield json.dumps(doc)


def random_date():
    current_datetime = datetime.now()

    random_timedelta = timedelta(
        days=random.randint(0, 365),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
        microseconds=random.randint(0, 999999)
    )

    random_datetime = current_datetime - random_timedelta
    return random_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f%z")


def generate_summary(details):
    sentences = details.split(". ")
    if len(sentences) > 1:
        summary = sentences[0] + "."
    else:
        summary = details
    return summary


def create_report(i):
    country = random.choice(countries)
    group = random.choice(groups)
    details = random.choice(details_options).format(country["name"], group, generate_selector())
    summary = generate_summary(details)
    report = {
        "report_id": f"INT-2024-{i+1:03d}",
        "date": random_date(),
        "source": random.choice(sources),
        "group": group,
        "country.name": country["name"],
        "country.coordinates": country["coordinates"],
        "country.code": country["code"],
        "summary": summary,
        "details": details,
        "classification": random.choice(classifications),
        "compartments": random.sample(compartments, random.randint(1, 4))
    }
    return report


def parse_filters(filters: dict) -> dict:
    must = []

    # parse date range
    if filters["date_range"] == "Last 30 Days":
        date_filter = {"range": {"date": {"gte": "now-30d"}}}
        must.append(date_filter)
    elif filters["date_range"] == "This Year":
        date_filter = {"range": {"date": {"gte": "2024-01-01"}}}
        must.append(date_filter)

    # parse countries selection
    if len(filters["countries"]) > 0:
        country_filter = {"terms": {"country.name": filters["countries"]}}
        must.append(country_filter)

    # parse classifications selection
    if len(filters["classifications"]) > 0:
        classification_filter = {"terms": {"classification": filters["classifications"]}}
        must.append(classification_filter)

    # parse sources selection
    if len(filters["sources"]) > 0:
        source_filter = {"terms": {"source": filters["sources"]}}
        must.append(source_filter)

    # parse compartments selection
    if len(filters["compartments"]) > 0:
        compartment_filter = {"terms": {"compartments": filters["compartments"]}}
        must.append(compartment_filter)

    final_filters = {"bool":{"must":must}}
    return final_filters


def elasticsearch_basic(query_text: str, filters: dict) -> dict:
    logging.info(f"Performing Elasticsearch basic query for user search: {query_text}")
    search_filters = parse_filters(filters)
    es_query = {
        "size": 3,
        "retriever": {
            "standard": {
                "query": {
                    "query_string": {
                        "default_field": "details",
                        "query": query_text,
                    }
                },
                "filter": search_filters
            }
        },
        "highlight": {
            "pre_tags": ["**:violet-background["],
            "post_tags": ["]**"],
            "fields": {"details": {"number_of_fragments": 0}},
        },
    }
    res = es.search(index=config["ELASTIC_INDEX"], body=es_query)
    hits = [hit["_source"] | hit["highlight"] for hit in res["hits"]["hits"]]
    return {"source_docs": hits}


def elasticsearch_elser(query_text: str, filters: dict) -> dict:
    logging.info(
        f"Performing Elasticsearch sparse vector query for user search: {query_text}"
    )

    search_filters = parse_filters(filters)
    es_query = {
        "size": 3,
        "retriever": {
            "standard": {
                "query": {
                    "sparse_vector": {
                        "field": "details_embeddings",
                        "inference_id": ".elser_model_2_linux-x86_64",
                        "query": query_text,
                    }
                },
                "filter": search_filters
            }
        },
    }
    res = es.search(index="intel-reports", body=es_query)
    hits = [hit["_source"] for hit in res["hits"]["hits"]]
    return {"source_docs": hits}


def llm(query_text: str) -> dict:
    logging.info(f"Performing LLM passthrough query for user search: {query_text}")

    response = open_ai_client.chat.completions.create(
        model=model_name,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
                    Assistant is a large language model trained by OpenAI. 
                    Be succint, answer in 15 words or less. 
                    If you don't know the answer, say that you don't know. 
                    Don't hallucinate. 
                    Don't ask follow up questions.
                    Do not include the number of words in your response.
                """,
            },
            {"role": "user", "content": query_text},
        ],
    )
    return {"llm_response": response.choices[0].message.content.strip()}


def rag(query_text: str, filters: dict) -> dict:
    logging.info(f"Performing RAG query for user search: {query_text}")
    es_hits = elasticsearch_elser(query_text, filters)["source_docs"]
    prompt = f"""
        Intelligence Reports:
        {str(es_hits)}

        Instructions:
        Answer the user's question using the intelligence reports text above only.
        Answer as if you are addressing a US intelligence analyst or Military officer.
        Keep in mind today's date is {today}.
        Keep your answer grounded in the facts of the intelligence reports.
        Summarize the intelligence report's details field and respond using 20 words or less.
        Do not include the number of words in your response.
    """

    logging.info(
        "Performing RAG search step 2 to LLM using Elasticsearch results as context"
    )
    # send the hits into the LLM as context
    success = False
    while not success:
        response = open_ai_client.chat.completions.create(
            temperature=0,
            model=model_name,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query_text},
            ],
        )
        # check if the response got filtered by content filter
        if hasattr(response.choices[0], "content_filter_results"):
            cfr = response.choices[0].content_filter_results
            if any(item.get("filtered", False) for item in cfr.values()):
                logging.warn("Failed due to content filtering. Retrying")
                time.sleep(1)
            else:
                success = True
                print(f"Success {response.to_json}")
                return {
                    "llm_response": response.choices[0].message.content.strip(),
                    "source_docs": es_hits,
                }
        else:
            return {
                "llm_response": response.choices[0].message.content.strip(),
                "source_docs": es_hits,
            }


def search(query_text: str, search_method: str, filters: dict) -> tuple:
    if search_method == "**Elasticsearch Basic**":
        response = elasticsearch_basic(query_text, filters)
        if len(response["source_docs"]) == 0:
            text = "No results found."
        else:
            text = "See below for reports."
        return text, response["source_docs"]

    elif search_method == "**ELSER**":
        response = elasticsearch_elser(query_text, filters)
        if len(response["source_docs"]) == 0:
            text = "No results found."
        else:
            text = "See below for reports."
        return text, response["source_docs"]

    elif search_method == "**LLM**":
        response = llm(query_text)
        return response["llm_response"], None

    elif search_method == "**RAG w/ ELSER**":
        response = rag(query_text, filters)
        return response["llm_response"], response["source_docs"]


def get_classification_level(classification: str) -> int:
    level_map = {
        "UNCLASSIFIED": 0,
        "HUSH HUSH": 1,
        "SUPER SECRET": 2,
        "ULTRA SUPER SECRET": 3,
    }
    return level_map[classification]  


def main():
    # top header
    st.header("GenAI-Powered Intelligence Analysis", divider="grey")

    # sidebar
    st.sidebar.image(".streamlit/logo-elastic-horizontal-color.png", width=100)
    st.sidebar.markdown("## Search Filter Options")
    date_range_selection = st.sidebar.selectbox(
        label="Date Range", 
        options=("All Time", "Last 30 Days", "This Year")
    )
    classification_selection = st.sidebar.multiselect(
        label="Classification",
        help="Defaults to All",
        placeholder="Select one or more",
        options=classifications
    )
    country_selection = st.sidebar.multiselect(
        label="Countries of Interest",
        help="Defaults to All",
        placeholder="Select one or more",
        options=[country["name"] for country in countries]
    )
    source_selection = st.sidebar.multiselect(
        label="Sources",
        help="Defaults to All",
        placeholder="Select one or more",
        options = sources
    )
    compartment_selection = st.sidebar.multiselect(
        label="Compartments",
        help="Defaults to All",
        placeholder="Select one or more",
        options = compartments
    )
    if not config["ELASTIC_CLOUD_ID"].endswith("MWY3ZGMzYjk0Lmti"): # demo cluster is protected
    # if not config["ELASTIC_CLOUD_ID"].endswith("xyz123"): # demo cluster is protected
        if st.sidebar.checkbox("Data Setup"):
            if st.sidebar.button(label="Generate and index intel reports", type="primary"):
                # create reports
                logging.info(f"Creating {config['NUM_REPORTS']} fake intel reports")
                intelligence_reports = []
                for i in range(config["NUM_REPORTS"]):
                    report = create_report(i)
                    intelligence_reports.append(report)

                # setup Elasticsearch
                setup_es(es, reset=True)

                # ingest reports into Elasticsearch
                ok, err = bulk_ingest(es, config["ELASTIC_INDEX"], intelligence_reports + precanned_events)
                if not ok:
                    st.sidebar.write(err)

                else:
                    # reset index settings back to normal settings now that ingest is complete
                    # settings = {"index": {"number_of_replicas": "1", "refresh_interval": "1s"}}
                    # es.indices.put_settings(index=config["ELASTIC_INDEX"], settings=settings)

                    st.sidebar.markdown("**Done!**")

    # search method options
    search_method = st.radio(
        "Choose search method:",
        [
            "**Elasticsearch Basic**",
            "**ELSER**",
            "**LLM**",
            "**RAG w/ ELSER**",
        ],
        horizontal=True,
    )
    st.write("")

    # input search bar
    search_query = st.text_input(
        "Enter search query and hit enter to search:",
        value="",
    )
    if search_query:
        with st.spinner("Searching..."):
            filters = {
                "date_range": date_range_selection,
                "classifications": classification_selection,
                "sources": source_selection,
                "countries": country_selection,
                "compartments": compartment_selection
            }
            text_result, json_result = search(search_query, search_method, filters)
        st.write("")
        st.markdown(f"##### **{text_result}**")
        st.write("")
        if json_result:
            report_classifications = [report["classification"] for report in json_result]
            st.markdown(
                f"*Highest classification of returned results: {max(report_classifications, key=get_classification_level)}*"
            )
            for x in range(len(json_result)):
                doc = json_result[x]
                with st.expander(f"**Intelligence Report ID {doc["report_id"]}** - {doc["summary"][:65]}..."):
                    st.markdown(f"**Classification**: {doc["classification"]}")
                    st.markdown(f"**Compartments**: {', '.join(doc["compartments"])}")
                    st.markdown(
                        f"**Report Date**: {datetime.strptime(doc["date"], "%Y-%m-%dT%H:%M:%S.%f").strftime("%A, %B %d, %Y")}"
                    )
                    st.markdown(f"**Summary**: {doc["summary"]}")
                    st.markdown(f"**Country**: {doc["country.name"] if "country.name" in doc else doc["country"]["name"]}")
                    st.markdown(f"**Source of Intel**: {doc["source"]}")
                    if isinstance(doc["details"], list):
                        st.markdown(f"**Details**: {doc["details"][0]}")
                    else:
                        st.markdown(f"**Details**: {doc["details"]}")

            st.write("")
            st.write("")
            with st.expander(
                "Below are the raw documents from ES that informed this answer:"
            ):
                st.json(json_result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Frontend web app for RAG intel analysis search demo"
    )
    parser.add_argument(
        "-c", "--config", action="store", dest="config_path", default="config.toml"
    )
    args = parser.parse_args()

    config = read_config(args.config_path)

    es = connect_es(config)

    if "LOCAL_LLM" in config and ( config["LOCAL_LLM"] == "True" or config["LOCAL_LLM"] == "true" ):
        logging.info("Local LLM selected via config. Using locally hosted LLM")
        open_ai_client = connect_self_hosted_llm(
            config["LOCAL_LLM_URL"], config["LOCAL_LLM_API_KEY"]
        )
        model_name = config["LOCAL_LLM_MODEL"]
    else:
        logging.info("Using Azure OpenAI LLM")
        open_ai_client = connect_open_ai(
            config["AZURE_OPENAI_API_KEY"],
            config["AZURE_API_VERSION"],
            config["AZURE_ENDPOINT"],
            config["AZURE_DEPLOYMENT"],
        )
        model_name = config["AZURE_MODEL"]

    start_date = datetime(2023, 5, 1)
    end_date = datetime(2024, 4, 3)

    countries = read_file("data/countries.json")
    groups = read_file("data/groups.json")
    sources = read_file("data/sources.json")
    details_options = read_file("data/details.json")
    classifications = read_file("data/classifications.json")
    compartments = read_file("data/compartments.json")
    precanned_events = read_file("data/precanned-events.json")

    main()
