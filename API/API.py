import sys
from datetime import datetime
#for handling requests and responses
from flask import Flask, jsonify, request, make_response
# this line is for the search engine
from googleapiclient.discovery import build
# for hebrew and arabic words
from urllib.parse import quote, unquote

# this line allows python to find our module.
sys.path.append('..\\SQL')
from SQL.SqlQueries import *
import re

def parse_google_search_query(query):
    """
    Parses a Google search query and returns a dictionary with the
    different search components separated into lists.
    
    Supported search components:
        - Keywords
        - Phrases (enclosed in quotes)
        - Excluded words (preceded by '-')
        - Positive words (preceded by '++')
        - Negative words (preceded by '--')
        - Sites (preceded by 'site:')
        - Date range (specified as 'after:' or 'before:')
    
    Args:
        query (str): The Google search query to parse.
    
    Returns:
        dict: A dictionary with the different search components separated
        into lists.
    """


    phrases = []
    positive_keywords = []
    negative_keywords = []
    excluded_keywords = []
    site = None
    datarange = None
    if not query:
        return {
        'phrases': phrases,
        'positive_keywords': positive_keywords,
        'negative_keywords': negative_keywords,
        'excluded_keywords': excluded_keywords,
        'site': site,
        'datarange': datarange,
        'keywords': keywords,
    }
    # find all phrases in the query and add them to the phrases list
  
    phrases = re.findall(r'"([^"]+)"', query)
    
    # remove phrases from query
    query = re.sub(r'"[^"]+"', '', query)
    
    # find all positive keywords in the query and add them to the positive_keywords list
    positive_keywords = re.findall(r'\+\+?\w+', query)
    
    # remove positive keywords from query
    query = re.sub(r'\+\+?\w+', '', query)
    
    # find all negative keywords in the query and add them to the negative_keywords list
    negative_keywords = re.findall(r'--?\w+', query)
    
    # remove negative keywords from query
    query = re.sub(r'--?\w+', '', query)
    
    # find all excluded keywords in the query and add them to the excluded_keywords list
    excluded_keywords = re.findall(r'-\w+', query)
    
    # remove excluded keywords from query
    query = re.sub(r'-\w+', '', query)
    
    # find site and datarange components in the query
    site = re.findall(r'site:\S+', query)
    datarange = re.findall(r'daterange:\S+', query)
    
    # remove site and datarange components from query
    query = re.sub(r'site:\S+', '', query)
    query = re.sub(r'daterange:\S+', '', query)
    
    # remove any remaining whitespace from query
    query = query.strip()
    
    # add any remaining words in query to keywords list
    keywords = re.findall(r'\w+', query)
    
    # return dictionary of extracted information
    return {
        'phrases': phrases,
        'positive_keywords': positive_keywords,
        'negative_keywords': negative_keywords,
        'excluded_keywords': excluded_keywords,
        'site': site[0].replace('site:', '') if site else None,
        'datarange': datarange[0].replace('daterange:', '') if datarange else None,
        'keywords': keywords,
    }
# creating a Flask app
app = Flask(__name__)


@app.route('/rows', methods=['POST'])
def default_select_table():
    select_all = SQLQuery()
    table = select_all.select_articles_from_sql()
    return make_response(jsonify(results=table), 200)


@app.route('/clear', methods=['POST'])
def clear_table():
    clear_query = SQLQuery()
    clear_query.clear_table()
    return make_response("table cleared", 200)

def get_default_websites():
    websites_to_search= ["www.ynet.co.il","www.israelhayom.co.il"] 
    return  websites_to_search

def scrap_links(links_to_scrap,keywords_intonation_list,phrase_intonation_list,category='1'):
    #TODO: scrap phrases and keywords differently
    '''
    scrapping information about each keyword and website
    then inserting them into the databse

    parameters:
    links_to_scrap: the dictionary we get from the custom google search engine
    keywords_intonation_list: a list of tuples, each tuple is (keyword,its intonation)
    when intonation is positive,negative or neutral
    category: the current query we are scrapping, currently placeholders
    for comparison

    notes: some websites are forbidden to scrap and we can't access to them
    '''
    if 'items' in links_to_scrap.keys():
        for item in links_to_scrap['items']:
            try:
                article_info=Article(item['link'])
                rows_to_add=article_info.create_rows_to_database(keywords_intonation_list,
                phrase_intonation_list,
                category)
                insert_query=SQLQuery()
                insert_query.insert_article_to_sql(rows_to_add)
            except HTTPError:
                make_response("This website is forbidden to scrap",403)   

def do_search_query(category='1'):
    '''
    Performs a Google search query (only keywords, no additional parameter).
    Scrapes from the links we found and updates the database.

    Parameters:
    category: the number of the current category we are scraping for
    '''
    query = request.json.get('Query'+category, "")  # assuming Query is the keywords

    # Parse the query
    query_dict = parse_google_search_query(query)
    keywords = query_dict["keywords"]
    phrases = query_dict["phrases"]
    positive_keywords = query_dict["positive_keywords"]
    negative_keywords = query_dict["negative_keywords"]
    excluded_keywords = query_dict["excluded_keywords"]
    site = query_dict["site"]
    datarange = query_dict["datarange"]

    # Get the list of websites to search
    site_list = get_default_websites()
    if site is not None:
        site_list.append(site)

    # Perform the search and scrape the links for each website
    for website in site_list:
        search_results = search_google(query, website)
        keyword_to_intonation,phrase_to_intonation = map_keywords_to_intonation(
            keywords_list=keywords,
            phrases=phrases,
            positive_keywords=positive_keywords,
            negative_keywords=negative_keywords
        )
        scrap_links(search_results, keyword_to_intonation,phrase_to_intonation, category)



# request of regular query
@app.route('/query', methods=['POST'])
def get_database_query():
    '''
    search and scrap 2 categories, and then return a response when finished
    '''
    do_search_query('1')
    # do_search_query('2')
    return make_response("OK", 200)  


def search_google(query, site_list, exclude_query=''):
    service = build("customsearch", "v1", developerKey="AIzaSyAsr-bDeoZiMP4KBzDNkqbFNNl49RLQbWE")
    result = service.cse().list(q=query, cx='0655ca3f748ac4757', siteSearch=site_list, excludeTerms=exclude_query, fileType='-pdf').execute()
    return result


def parse_json_and_strip(json_field):
    '''
    searches for an element with the name json_field
    if exists, returns a list of the content of that field
    if not, returns empty list
    '''
    field_content = request.json.get(json_field, [])
    if field_content == []:
        return []
    return field_content


def parse_table_rows(rows):
    '''
    when returning a select query, it returns as a list of tuple [(row1),(row2),...]
    '''
    return [row[0] for row in rows]


def include_exclude_lists(universe, included, excluded):
    '''
    prevents repetition in searching included and excluded keywords, websites etc.
    | is the union operator
    '''
    return list((set(universe) | set(included)) - set(excluded))


def create_parameters_list(included_field, excluded_field):
    '''
    returns a list of the parameters we want in the search, and without the ones we want to exclude
    '''
    included_parameters = parse_json_and_strip(included_field)
    excluded_parameters = parse_json_and_strip(excluded_field)
    return include_exclude_lists([], included_parameters, excluded_parameters)


def is_at_least_one_keyword(category='1'):
    '''
    any request requires at least one keyword, bad request otherwise
    '''
    included_keywords = parse_json_and_strip('included_keywords'+category)
    return included_keywords != []

def map_keywords_to_intonation(keywords_list,phrases,positive_keywords,negative_keywords):
    '''
    uses the existing keyword database and queries to map a keyword to the intonation
    (if exists already)
    '''
    
    known_keyword_to_intonation = SQLQuery().select_learned_keywords()
    if known_keyword_to_intonation is None:
        known_keyword_to_intonation={}
    phrases_no_quotes = [phrase.strip('"\'') for phrase in phrases]

    # Process keywords
    keyword_to_intonation = [
        (keyword, known_keyword_to_intonation[keyword] if keyword in known_keyword_to_intonation else 
         'positive' if keyword in positive_keywords else 
         'negative' if keyword in negative_keywords else 
         'neutral')
        for keyword in keywords_list
    ]

    # Process phrases
    phrase_to_intonation = [
        (phrase, known_keyword_to_intonation[phrase] if phrase in known_keyword_to_intonation else 
         'positive' if phrase in positive_keywords else 
         'negative' if phrase in negative_keywords else 
         'neutral')
        for phrase in phrases_no_quotes
    ]
    #TODO:replace with NLP once we have it
    filtered_learned_words = [(s1, s2) for s1, s2 in keyword_to_intonation+phrase_to_intonation if s2 != "neutral"]
    SQLQuery().insert_keyword_intonation_to_sql(filtered_learned_words)
    return keyword_to_intonation, phrase_to_intonation

def advanced_search_query(category='1'):
    '''
    performs scrapping based on all the advanced search parameters.
    the only mandatory one is keywords
    '''
    if not is_at_least_one_keyword():
        # return bad request error
        return make_response("Searching requires at least one keyword", 400)
    #returns string
    keywords_json=request.json.get('included_keywords' + category, "")
    keywords_to_search=keywords_json


    websites_to_search = list(set(parse_json_and_strip('included_sites' + category)) | 
                              set(get_default_websites()))
    
    # assumption: time range would be just two dates separated by comma
    time_range = parse_json_and_strip('date_range'+category)
    # no dates were passed
    if not time_range:
        # either default range or just not searching by range at all
        datetime_range = [datetime(year=datetime.now().year - 1, month=1, day=1), datetime.now()]
    else:
        try:
            datetime_range = [datetime.strptime(date_string, "%Y-%m-%d") for date_string in time_range]
        except ValueError:
            return make_response("The date format is incorrect, please make sure the format is year-month-day", 400)
    
  



    negative_words=[]
    negative_json=request.json.get('negative_words' + category, "")
    if negative_json:
        negative_words=negative_json
        



    positive_words=[]
    positive_json=request.json.get('positive_words' + category, "")
    if positive_json:
        positive_words=positive_json

    keywords_to_exclude =parse_json_and_strip('excluded_keywords'+category)

    words_to_insert=[(word,'negative') for word in negative_words]
    words_to_insert.extend([(word,'positive') for word in positive_words])
    SQLQuery().insert_keyword_intonation_to_sql(words_to_insert)

    #TODO: add phrases list here
    keyword_to_intonation,phrases_to_intonation=map_keywords_to_intonation(keywords_to_search,[],
                                                                           positive_words,negative_words)

   

    # URL-encode the search keywords
    _, decoded_keywords = url_encode_keywords(keywords_to_search)
    query = ','.join(decoded_keywords)

    # URL-encode the exclude keywords
    _, decoded_exclude = url_encode_keywords(keywords_to_exclude)
    exclude_query = ','.join(decoded_exclude)
    
    for website in websites_to_search:
        links_to_scrap = search_google(query, website, exclude_query)
        scrap_links(links_to_scrap,keyword_to_intonation,phrases_to_intonation,category)
    # TODO: specify dates in the google search

def url_encode_keywords(keywords):
    """
    URL-encodes a list of keywords using UTF-8 encoding and returns the encoded and decoded values.

    Args:
        keywords (list): A list of keywords to encode.

    Returns:
        A tuple containing two lists: the first list contains the URL-encoded and UTF-8 encoded keywords,
        and the second list contains the decoded keywords.
    """
    encoded_keywords = [quote(keyword.encode('utf-8')) for keyword in keywords]
    decoded_keywords = [unquote(keyword) for keyword in encoded_keywords]
    return encoded_keywords, decoded_keywords

@app.route('/advancedSearch', methods=['POST'])
def advanced_search():
    '''
    api response to advanced search
    searching with tags such as included/exluded keywords,websites, date range and so on
    adds the information by category to the database for display in the frontend later
    returns bad request if there are no keywords in the search query
    otherwise returns ok
    '''
    advanced_search_query('1')
    
    # not adding specified statistics yet, because there is only counter for now
    return make_response("ok", 200)


# driver function
if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=False, port=10000)
