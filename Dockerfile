FROM python:3.7-buster

COPY . .

RUN pip install -r requirements.txt
CMD streamlit run tool.py
