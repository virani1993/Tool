import re
import pdftotext
import streamlit as st
import pandas as pd
from scipy.spatial.distance import cosine
from snowballstemmer import EnglishStemmer  # Use snowball stemming for turkish stemming
from sklearn.feature_extraction.text import CountVectorizer

engStem = EnglishStemmer()
all_stopwords = []  # Add stopwords if needed.


@st.cache
def clean_pdf_page(page):  # Cleans a pdftotext page
    """Takes a long string represeting a page and returns the cleaned sentences
    
    Returns:
        list -- list of sentences
    """
    return [re.sub("\s+", " ", i.strip()) for i in page.split("\n")]


def read_pdf_file(file):
    """Converts a file to a pdftotext object
    
    Arguments:
        file {file} -- PDF File
    
    Returns:
        pdftotext.PDF -- pdftotext representation of the file
    """
    return pdftotext.PDF(file)


@st.cache
def get_sections(pages):
    """Get the different sections in a given page
    
    Arguments:
        pages {list} -- list of pages to extract sections from
    
    Returns:
        dict -- Dictionary containing the section names and their values
    """
    sections = {}
    section_pages = {}
    current_section_name = None
    current_section = []

    for page_num, page in enumerate(pages):
        clean_page = [re.sub("\s+", " ", i.strip()) for i in page.split("\n")]

        for ind, i in enumerate(clean_page):

            if (
                re.findall("^Section \d+", i)
                and "page" not in i
                or (re.sub("\d+ [\w+\s+]+", "", i) == "" and ind == 0 and len(i) > 6)
            ):
                if current_section_name is not None:
                    sections[current_section_name] = current_section
                    current_section = []
                current_section_name = i
                break

        section_pages[page_num + 1] = current_section_name or "No Section"

        current_section.extend(clean_page)
    return sections, section_pages


@st.cache(allow_output_mutation=True, suppress_st_warning=True)
def calculate_distance(df1, df2):
    """Calculate the cosine distance between all vectors in two dataframes
    
    Arguments:
        df1 {DataFrame} -- Dataframe of first set of features
        df2 {DataFrame} -- Dataframe of second set of features
    
    Returns:
        Dataframe -- Dataframe containing the distances between the vectors
    """
    my_bar = st.progress(0)
    total_length = df1.shape[0] * df2.shape[0]
    incr = 0.0
    output = {}
    for ind in df1.index:
        output[ind] = {}
        for ind2 in df2.index:
            output[ind][ind2] = cosine(df1.loc[ind], df2.loc[ind2])
            incr += 1.0
            my_bar.progress(incr / total_length)

    return pd.DataFrame(output).dropna(how="all").dropna(how="all", axis=1)


@st.cache
def get_similar_sentences(df_1, df_2):
    """Using scikit-learn's count vectorizer, vectorize the two sets of text and find the best closest ones.
    
    Arguments:
        df_1['Sentance'] {list} -- list of first group of text
        df_2['Sentance'] {list} -- list of second group of text
    
    Returns:
        Dataframe -- Dataframe of all similar words and word pages between the two texts
    """
    cv = CountVectorizer(stop_words="english")

    cv.fit(pd.concat([df_1, df_2])["Sentance"])

    df_1_feat = pd.DataFrame(
        cv.transform(df_1["Sentance"]).toarray(), index=df_1["Sentance"].index
    )
    df_2_feat = pd.DataFrame(
        cv.transform(df_2["Sentance"]).toarray(), index=df_2["Sentance"].index
    )

    score = calculate_distance(df_1_feat, df_2_feat)

    score_vals = score.min()
    mins = score_vals[score_vals < 0.5].index
    results = []
    for i, j in score.idxmin().loc[mins].items():
        results.append(
            (
                df_1["Sentance"].loc[i],
                df_1["Page"].loc[i],
                df_2["Sentance"].loc[j],
                df_2["Page"].loc[j],
            )
        )
    return pd.DataFrame(
        results,
        columns=["File 1 Sentance", "File 1 Page", "File 2 Sentance", "File 2 Page"],
    )


@st.cache
def clean_text(text):
    """Clean a text by lowering the text, removing symbols and stopwords.
    
    Arguments:
        text {string} -- string to clean
    
    Returns:
        string -- cleaned string
    """
    text = text.lower()  # Convert the text to lower case
    text = re.sub(",", " ", text)  # Replace commas with an extra space

    text = re.sub("<.*?>", "", text)  # Clean out any HTML tags
    text = re.sub("\s+", " ", text)  # Replace multiple spaces with

    text = text.split()

    text = [
        re.sub("[^\w]", "", i.rstrip()) for i in text if i not in all_stopwords
    ]  # Clean out stopwords

    # text = engStem.stemWords(text)# English Stemming

    text = " ".join(text)
    return text
