import streamlit as st
from analytics import (
    get_words_in_sentances,
    get_headers,
    get_frequent_words,
    get_comparison_similar_words,
    get_figures_tables,
    run_query,
    get_money,
    get_associated_words,
)
from utils import read_pdf_file, get_sections
import base64
import pickle
import os
import json
import plotly.graph_objs as go
import pandas as pd

BACKUP_FILE = "db.json"
CLASS_MAPPER = "class.json"

db = {}
cm = {}
if os.path.exists(BACKUP_FILE):
    db = json.load(open(BACKUP_FILE, "r+"))

if os.path.exists(CLASS_MAPPER):
    cm = json.load(open(CLASS_MAPPER, "r+"))

TOOL_OPTIONS = [
    "Should, Shall, Must",
    "Headers",
    "Query",
    "Section Words",
    "Table & Figures",
    "Scored Query",
    "Scored Should, Shall, Must",
    "Price Search",
]

COMPARE_OPTIONS = ["Should, Shall, Must", "Query Comparison"]

DOWNLOAD_BUTTON_STYLE = """
    background-color:#37a879;
    border-radius:28px;
    border:1px solid #37a879;
    display:inline-block;
    cursor:pointer;
    color:#ffffff;
    font-family:Arial;
    font-size:12px;
    padding:8px 15px;
    text-decoration:none;
    text-shadow:0px 1px 0px #2f6627;
"""


def display_result(df, filename, header):
    """Display a dataframe along with the option to download the data.
    
    Arguments:
        df {pd.DataFrame} -- Dataframe to display
        filename {str} -- Name of file to downlaod
        header {str} -- Title of dataframe
    """
    st.header(header)
    st.table(df)
    st.markdown(download_button(df, filename), unsafe_allow_html=True)


def display_words(word_dict, fig=False, target=None, key_incr=0):
    """Function used to display multiple sub-groups of words
    
    Arguments:
        word_dict {dict} -- Dictionary with the following format: {Word: DataFrame}
    """
    for word in word_dict:
        key = word
        word = word.replace("_2", "")
        if word == "should":
            st.header("Hard Requirements")
        elif word == "shall":
            st.header("Soft Requirements")

        if word in word_dict:
            word_btn = st.checkbox(
                word.title() + " - " + str(word_dict[word].shape[0]),
                key=key + f"{key_incr}_button",
            )
            if word_btn:
                if fig:
                    plot_distributions(word_dict[key], target)
                display_result(word_dict[key], word.title() + ".csv", word.title())


def plot_distributions(df, target):
    if df.shape[0] > 0 and df.shape[1] > 0:
        df[target] = df[target].apply(lambda x: " ".join(x.split()[:2]))
        new_df = df[target].value_counts() / df.shape[0]
        fig = go.Figure(
            [
                go.Bar(
                    x=new_df.index,
                    y=new_df.values,
                    text=(new_df * 100).round(2).astype(str) + "%",
                    textposition="auto",
                )
            ],
            layout=dict(
                width=1000,
                height=700,
                font=dict(size=15),
                yaxis=dict(tickformat="%", title="Distribution"),
                title="Section Scores",
            ),
        )
        fig.update_xaxes(automargin=True)
        st.write(fig)


def download_button(df, filename="download"):
    csv = df.to_csv()
    b64 = base64.b64encode(
        csv.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a name="download" href="data:file/csv;base64,{b64}" download="{filename}.csv">\
        <button style="{DOWNLOAD_BUTTON_STYLE}">Download Figure Data</button></a>'
    return href


file_mode = st.selectbox("Select Input Type", options=["PDF", "Excel"])


def get_pages_ui(key=1):
    
    st.markdown("________")
    pages = None
    sections = None
    name = None
    if file_mode == "PDF":
        mode = st.selectbox(
            "Selection Mode",
            ["New File", "Existing File"] if db else ["New File"],
            key=f"selection_{key}",
        )
        if mode == "New File":
            name = st.text_input("Filename", key=f"name_{key}")
            uploaded_class = st.text_input(
                "CHoose a Class Name for this File",
                "Automobile",
                key=f"class_text_name_{key}",
            )

            uploaded_file = st.file_uploader(
                "Choose a PDF file", type="pdf", key=f"file_uploader_{key}"
            )
            if uploaded_file is not None:
                pages = get_pages(uploaded_file)
                _, sections = get_sections(pages)

        else:
            count_class = {i: len(j) for i, j in cm.items()}
            st.write(pd.Series(count_class, name="Count"))
            uploaded_class = st.selectbox(
                "Previous File Class", sorted(list(cm.keys())), key=f"class_name_{key}"
            )

            if uploaded_class:
                file_name = st.selectbox(
                    "Previous File",
                    sorted(list(cm[uploaded_class])),
                    key=f"file_name_{key}",
                )
                if file_name:
                    pages = db[file_name]
                    _, sections = get_sections(pages)
                    name = file_name
    else:
        uploaded_class = st.text_input(
                "CHoose a Class Name for this File",
                "Automobile",
                key=f"class_text_name_{key}",
            )
        name = st.text_input("Filename", key=f"name_{key}")
        uploaded_file = st.file_uploader(
            "Choose a Excel file", type="xlsm", key=f"file_uploader_{key}"
        )
        if uploaded_file is not None:
            pages = list(
                pd.read_excel(uploaded_file).iloc[:, 1].astype(str).values.reshape(-1)
            )
            _, sections = get_sections(pages)
    st.markdown("________")
    if pages:
        st.info(
            f"**Insights on {name}** \n* **Class**: {uploaded_class} \n * **# of Pages**: {len(pages)} \n  * **# of Sections**: {len(set(sections.values()))}"
        )
    return pages, sections, name, uploaded_class


st.title("PDF Tool")
st.header("Singular File Exploration")


@st.cache
def get_pages(file):
    """Get list of all pages in a pdf file
    
    Arguments:
        file {file} -- Input PDF file
    
    Returns:
        list -- List of all pages in pdf
    """
    pdf = read_pdf_file(file)
    pages = [i for i in pdf]
    return pages


@st.cache
def get_pages_excel(df):
    return list(df.iloc[:, 1].values)


pages, sections_1, name, class_name = get_pages_ui()

if pages is not None and name:
    multi_select = st.selectbox(
        "Choose Tool Output", options=TOOL_OPTIONS, key="first_file_mulit"
    )
    if multi_select == TOOL_OPTIONS[0]:
        word_results = get_words_in_sentances(
            pages, ["should", "must", "shall"], sections_1
        )
        d = pd.Series({i: j.shape[0] for i, j in word_results.items()})
        st.write(d)
        st.write(go.Figure(data=[go.Pie(labels=d.index, values=d.values)]))

        display_words(word_results, fig=True, target="Section")
        st.markdown("____")
        st.subheader("Associated Words")
        display_words(get_associated_words(pages, ["should", "must", "shall"], sections_1), key_incr=3)
    elif multi_select == TOOL_OPTIONS[1]:
        display_result(get_headers(pages), "headers", "Headers")
    elif multi_select == TOOL_OPTIONS[2]:
        st.header("Searching the PDF")
        st.warning(
            "Example Queries: **Safety, Dimension, Standard, Regulation, Ambient Temperature**"
        )
        query = st.text_input("Please enter a query to search", key="query_input")
        if query:
            results = get_words_in_sentances(pages, [query])
            display_words(results)
    elif multi_select == TOOL_OPTIONS[3]:
        word_results = get_frequent_words(pages)
        display_words(word_results)
    elif multi_select == TOOL_OPTIONS[4]:
        word_results = get_figures_tables(pages, sections_1)
        display_words(word_results)
    elif multi_select == TOOL_OPTIONS[5]:
        query_count = st.slider("Query Amount", 2, 5, key="q_slider")
        all_queries = []
        for i in range(query_count):
            qw = st.text_input(f"Query Word {i+1}", key=f"query{i}_input")
            qs = st.number_input(f"Query Score {i+1}", 1, 5, key=f"score{i}_input")
            all_queries.append((qw, qs))

        results, specific = run_query(pages, sections_1, all_queries)
        st.write(results.reset_index().rename(columns={"index": "Section Title"}))
        specific = {i: j for i, j in specific.items() if j}
        display_selection = st.selectbox("Score visualization", list(specific.keys()))
        d = pd.Series(specific[display_selection])
        st.write(go.Figure(data=[go.Pie(labels=d.index, values=d.values, hole=0.6)]))
    elif multi_select == TOOL_OPTIONS[6]:
        x = st.number_input("Must Coefficient", key="must_coef")
        y = st.number_input("Shall Coefficient", key="shall_coef")
        z = st.number_input("Should Coefficient", key="should_coef")
        score_run = st.button("Run Scoring!", key="run_score")
        if score_run:
            st.info(
                f"**req_freq_ind_score** = {x}**(Must)** + {y}**(Shall)** + {z}**(Should)**"
            )
            res, _ = run_query(
                pages, sections_1, [("must", x), ("shall", y), ("shoukd", z)]
            )
            res["Z-Score"] = res["Weight"].apply(
                lambda x: (x - res["Weight"].mean()) / res["Weight"].std()
            )
            st.write(res)
            st.info(
                f"""Average X-Score: {res["Weight"].mean().round(2)}  \n  STD X-Score: {res["Weight"].std().round(2)}"""
            )
    elif multi_select == TOOL_OPTIONS[7]:
        results = get_money(pages, sections_1)
        st.table(results)
    st.write("_______")
    st.header("Comparing Different Files")
    pages_2, sections_2, name_2, class_name_2 = get_pages_ui(key=2)

    if pages_2 is not None and name_2 and class_name_2:
        multi_select_2 = st.selectbox(
            "Choose Comparison Output", options=TOOL_OPTIONS, key="second_file_mulit"
        )

        if multi_select_2 == COMPARE_OPTIONS[0]:
            res = get_comparison_similar_words(pages, pages_2, ["should", "shall"],)
            display_words(
                res, key_incr=1
            )
        elif multi_select_2 == COMPARE_OPTIONS[1]:
            query = st.text_input("Please enter a query to search", key="query_input")
            run_query = st.button("Run Query!", key="run_query")
            if query:
                results = get_words_in_sentances(pages, [query])
                results_2 = get_words_in_sentances(pages_2, [query])
                display_words(results)
        cm.setdefault(class_name_2, [])
        if name_2 not in cm[class_name_2]:
            cm[class_name_2].append(name_2)

    cm.setdefault(class_name, [])
    if name not in cm[class_name]:
        cm[class_name].append(name)
    db[name] = pages
    json.dump(db, open(BACKUP_FILE, "w+"))
    json.dump(cm, open(CLASS_MAPPER, "w+"))

