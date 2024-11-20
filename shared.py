# *** Libraries
import os, json
from github import Github

# *** Functions
# Log a raw request and response (consisting of data + headers)
def log_raw(raw_out, request, result):
    raw_result = {
        'request': request
    }
    try:
        raw_result['raw_data'] = result.raw_data
    except:
        raw_result['raw_data'] = None

    try:
        raw_result['raw_headers'] = result.raw_headers
    except:
        raw_result['raw_headers'] = None
        
    print(json.dumps(raw_result, indent = 2))
    raw_out.append(raw_result)

# Make a raw request to the GitHub REST API via PyGithub
def get_request(gh, slug):
    response = gh.requester.requestJsonAndCheck("GET", gh.requester.base_url + slug)
    result = lambda: None
    result.raw_data = response[1]
    result.raw_headers = response[0]
    return result