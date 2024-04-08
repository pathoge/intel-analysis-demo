import argparse
import json
import logging
import random
import tomllib
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk, BulkIndexError


logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)


def read_config(config_path):
    logging.info("Reading config.toml")
    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    return config_data


def read_file(file_name):
    with open(file_name, "r") as file:
        data = json.load(file)
    return data


def setup_es(cloud_id, user, pw, index, reset):
    es = Elasticsearch(cloud_id=cloud_id, basic_auth=(user, pw))
    if reset and es.indices.exists(index=index):
        logging.info("Deleting existing index")
        es.indices.delete(index=index)

    if not es.indices.exists(index=index):
        logging.info("Creating index")
        mapping = {
            "properties": {
                "classification": {"type": "keyword"},
                "date": {"type": "date"},
                "details": {"type": "text"},
                "report_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "group": {"type": "keyword"},
                "summary": {"type": "text"},
                "summary_embeddings": {"type": "sparse_vector"},
                "country.name": {"type": "keyword"},
                "country.coordinates": {"type": "geo_point"},
                "country.code": {"type": "keyword"},
            }
        }
        settings = {
            "index": {
                "number_of_shards": "2",
                "number_of_replicas": "0",
                "refresh_interval": "-1",
            }
        }
        es.indices.create(index=index, mappings=mapping, settings=settings)

    return es


def bulk_ingest(es, index, docs):
    try:
        logging.info("Sending docs to ES")
        for ok, action in streaming_bulk(
            client=es, index=index, actions=yield_doc(docs)
        ):
            if not ok:
                logging.error(f"{ok} {action}")
    except BulkIndexError as e:
        print(f"{len(e.errors)} document(s) failed to index.")
        for error in e.errors:
            print(error)


def yield_doc(docs):
    for doc in docs:
        # print(json.dumps(doc))
        yield json.dumps(doc)


def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def generate_summary(details):
    sentences = details.split(". ")
    if len(sentences) > 1:
        summary = sentences[0] + "."
    else:
        summary = details
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a bunch of fake intel reports and index them in Elasticsearch"
    )
    parser.add_argument("-c", "--config", action="store", dest="config_path", default="config.toml")
    args = parser.parse_args()


    config_data = read_config(args.config_path)

    start_date = datetime(2023, 5, 1)
    end_date = datetime(2024, 4, 3)

    countries = read_file("countries.json")
    groups = read_file("groups.json")
    sources = read_file("sources.json")
    details_options = read_file("details.json")
    classifications = [
        "UNCLASSIFIED",
        "HUSH HUSH",
        "SUPER SECRET",
        "ULTRA SUPER SECRET",
    ]

    logging.info(f"Creating {config_data['NUM_REPORTS']} fake intel reports")
    intelligence_reports = []
    for i in range(config_data["NUM_REPORTS"]):
        country = random.choice(countries)
        group = random.choice(groups)
        details = random.choice(details_options).format(country["name"], group)
        summary = generate_summary(details)

        report = {
            "report_id": f"INT-2024-{i+1:03d}",
            "date": random_date(start_date, end_date).strftime("%Y-%m-%d"),
            "source": random.choice(sources),
            "group": group,
            "country.name": country["name"],
            "country.coordinates": country["coordinates"],
            "country.code": country["code"],
            "summary": summary,
            "details": details,
            "classification": random.choice(classifications),
        }
        intelligence_reports.append(report)

    es = setup_es(
        config_data["CLOUD_ID"],
        config_data["USER"],
        config_data["PASSWORD"],
        config_data["INDEX"],
        True,
    )
    bulk_ingest(es, config_data["INDEX"], intelligence_reports)
    settings = {"index": {"number_of_replicas": "1", "refresh_interval": "1s"}}
    es.indices.put_settings(index=config_data["INDEX"], settings=settings)
