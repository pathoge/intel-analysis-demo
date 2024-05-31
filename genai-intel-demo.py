import argparse
import streamlit as st
import logging
import tomllib
from datetime import datetime
from time import sleep
from elasticsearch import Elasticsearch
from openai import AzureOpenAI, OpenAI


logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)

today = datetime.today().strftime("%A, %B %d, %Y")

st.set_page_config(page_title="GenAI-Powered Intelligence Analysis", page_icon="🔍")

st.markdown(
    """
<style>
    [data-testid="stAppViewBlockContainer"] {
            padding: 3rem 1rem 10rem 1rem;
    }
    [data-testid="stSidebarUserContent"] {
            padding-top: 4rem;
	}
	[data-testid="stDecoration"] {
        background-image: none;
		background-color: #00BFB3;
	}
    [data-testid="stToolbar"] {
            display: none;
	}
    [data-testid=stSidebar] [data-testid=stImage]{
        text-align: center;
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
    [data-testid=stSidebar] [data-testid=stMarkdown]{
        text-align: center;
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 100%;
    }
    [data-testid=stSidebar] [data-testid=stButton]{
        text-align: center;
    }
    [data-testid=stTextInput] [data-testid=textInputRootElement] [data-baseweb="base-input"] {
        background-color: white;
    }
</style>""",
    unsafe_allow_html=True,
)


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


def connect_es(cloud_id: str, user: str, pw: str) -> Elasticsearch:
    es = Elasticsearch(cloud_id=cloud_id, basic_auth=(user, pw))
    return es


def read_config(config_path: str) -> dict:
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


def parse_filters(filters: dict) -> dict:
    date_range = "now-100y"
    if filters["date_range"] == "All Time":
        date_range = "now-1000y"
    elif filters["date_range"] == "Last 30 Days":
        date_range = "now-30d"
    elif filters["date_range"] == "This Year":
        date_range = "2024-01-01"

    return {"range": {"date": {"gte": date_range}}}


def elasticsearch_basic(query_text: str, filters: dict) -> dict:
    logging.info(f"Performing Elasticsearch basic query for user search: {query_text}")
    date_range = parse_filters(filters)
    query = {
        "size": 3,
        "query": {
            "bool": {
                "filter": [date_range],
                "must": [
                    {
                        "query_string": {
                            "default_field": "details",
                            "query": query_text,
                        }
                    }
                ],
            }
        },
        "highlight": {
            "pre_tags": ["**:violet-background["],
            "post_tags": ["]**"],
            "fields": {"details": {"fragment_size": 1000}},
        },
    }
    res = es.search(index=config["ELASTIC_INDEX"], body=query)
    hits = [hit["_source"] | hit["highlight"] for hit in res["hits"]["hits"]]
    return {"source_docs": hits}


def elasticsearch_elser(query_text: str, filters: dict) -> dict:
    logging.info(
        f"Performing Elasticsearch text expansion query for user search: {query_text}"
    )

    date_range = parse_filters(filters)

    # perform ES text_expansion query
    query = {
        "size": 3,
        "query": {
            "bool": {
                "filter": [date_range],
                "must": {
                    "text_expansion": {
                        "details_embeddings": {
                            "model_id": ".elser_model_2",
                            "model_text": query_text,
                        }
                    }
                },
            }
        },
    }
    res = es.search(index=config["ELASTIC_INDEX"], body=query)
    hits = [hit["_source"] for hit in res["hits"]["hits"]]
    return {"source_docs": hits}


def llm(query_text: str) -> dict:
    logging.info(f"Performing LLM passthrough query for user search: {query_text}")

    response = open_ai_client.chat.completions.create(
        model=model_name,
        # model="gpt-4o",
        # model="mixtral",
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
            # model="gpt-4o",
            # model="mixtral",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query_text},
            ],
        )
        # check if the response got filtered by content filter
        if hasattr(response.choices[0], "content_filter_results"):
            cfr = response.choices[0].content_filter_results
            if any(item.get("filtered", False) for item in cfr.values()):
                logging.info("Failed due to content filtering. Retrying")
                sleep(1)
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
    # post_data = json.dumps({"query_text": query} | {"filters": filters})
    if search_method == "**Elasticsearch Basic**":
        response = elasticsearch_basic(query_text, filters)
        return "See below for reports.", response["source_docs"]

    elif search_method == "**ELSER**":
        response = elasticsearch_elser(query_text, filters)
        return "See below for reports.", response["source_docs"]

    elif search_method == "**LLM**":
        response = llm(query_text)
        return response["llm_response"], None

    elif search_method == "**RAG w/ Elasticsearch**":
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
        "Date Range:", ("All Time", "Last 30 Days", "This Year")
    )
    classification_selection = st.sidebar.multiselect(
        "Classification",
        ["ALL", "UNCLASSIFIED", "HUSH HUSH", "SUPER SECRET", "ULTRA SUPER SECRET"],
        default=["ALL"],
    )
    country_selection = st.sidebar.multiselect(
        "Countries of Interest",
        ["ALL", "Afghanistan", "Albania", "Algeria", "Andorra"],
        default=["ALL"],
    )
    source_selection = st.sidebar.multiselect(
        "Sources", ["ALL", "GEOINT", "HUMINT", "SIGINT", "MASINT"], default=["ALL"]
    )

    # search method options
    search_method = st.radio(
        "Choose search method:",
        [
            "**Elasticsearch Basic**",
            "**ELSER**",
            "**LLM**",
            "**RAG w/ Elasticsearch**",
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
            }
            text_result, json_result = search(search_query, search_method, filters)
        st.write("")
        st.markdown(f"##### **{text_result}**")
        st.write("")
        if json_result:
            classifications = [report["classification"] for report in json_result]
            st.markdown(
                f"*Highest classification of returned results: {max(classifications, key=get_classification_level)}*"
            )
            for x in range(len(json_result)):
                doc = json_result[x]
                with st.expander(f"**Intelligence Report ID {doc["report_id"]}**"):
                    st.markdown(f"**Classification**: {doc["classification"]}")
                    st.markdown(f"**Compartments**: {', '.join(doc["compartments"])}")
                    st.markdown(
                        f"**Report Date**: {datetime.strptime(doc["date"], "%Y-%m-%dT%H:%M:%S.%f").strftime("%A, %B %d, %Y")}"
                    )
                    st.markdown(f"**Summary**: {doc["summary"]}")
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
    parser.add_argument(
        "-l", "--local-llm", action="store_true", dest="local_llm", default=False
    )
    args = parser.parse_args()

    config = read_config(args.config_path)

    es = connect_es(
        config["ELASTIC_CLOUD_ID"],
        config["ELASTIC_USER"],
        config["ELASTIC_PASSWORD"],
    )

    if args.local_llm:
        open_ai_client = connect_self_hosted_llm(
            config["LOCAL_LLM_URL"], config["LOCAL_LLM_API_KEY"]
        )
        model_name = config["LOCAL_LLM_MODEL"]
    else:
        open_ai_client = connect_open_ai(
            config["AZURE_OPENAI_API_KEY"],
            config["AZURE_API_VERSION"],
            config["AZURE_ENDPOINT"],
            config["AZURE_DEPLOYMENT"],
        )
        model_name = config["AZURE_MODEL"]

    main()
