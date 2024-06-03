FROM python:3.12

EXPOSE 8501
WORKDIR /app

COPY requirements.txt .
COPY genai-intel-demo.py .
COPY .streamlit/* .streamlit/
COPY data/*.json data/

RUN pip install -r requirements.txt

HEALTHCHECK CMD curl --fail http://localhost:8501/healthz

ENTRYPOINT ["streamlit", "run", "genai-intel-demo.py", "--server.port=8501", "--server.address=0.0.0.0"]