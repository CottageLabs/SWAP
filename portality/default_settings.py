from datetime import timedelta

SECRET_KEY = "default-key" # make this something secret in your overriding app.cfg
REMEMBER_COOKIE_DURATION = timedelta(minutes=60)
PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)

# contact info
ADMIN_NAME = "SWAP"
ADMIN_EMAIL = ""

# service info
SERVICE_NAME = "SWAP"
SERVICE_TAGLINE = ""
HOST = "0.0.0.0"
DEBUG = True
PORT = 5006

# list of superuser account names
SUPER_USER = ["test"]

PUBLIC_REGISTER = False # Can people register publicly? If false, only the superuser can create new accounts

# elasticsearch settings
ELASTIC_SEARCH_HOST = "http://127.0.0.1:9200"
ELASTIC_SEARCH_DB = "swap"
INITIALISE_INDEX = True # whether or not to try creating the index and required index types on startup
NO_QUERY_VIA_API = ['account','student'] # list index types that should not be queryable via the API
PUBLIC_ACCESSIBLE_JSON = True # can not logged in people get JSON versions of pages by querying for them?

# if search filter is true, anonymous users only see visible and accessible pages in query results
# if search sort and order are set, all queries from /query will return with default search unless one is provided
# placeholder image can be used in search result displays
ANONYMOUS_SEARCH_FILTER = False
SEARCH_SORT = ''
SEARCH_SORT_ORDER = ''


# a dict of the ES mappings. identify by name, and include name as first object name
# and identifier for how non-analyzed fields for faceting are differentiated in the mappings
FACET_FIELD = ".exact"
MAPPINGS = {
    "student" : {
        "student" : {
            "dynamic_templates" : [
                {
                    "default" : {
                        "match" : "*",
                        "match_mapping_type": "string",
                        "mapping" : {
                            "type" : "multi_field",
                            "fields" : {
                                "{name}" : {"type" : "{dynamic_type}", "index" : "analyzed", "store" : "no"},
                                "exact" : {"type" : "{dynamic_type}", "index" : "not_analyzed", "store" : "yes"}
                            }
                        }
                    }
                }
            ]
        }
    }
}
MAPPINGS['account'] = {'account':MAPPINGS["student"]["student"]}
MAPPINGS['course'] = {'course':MAPPINGS["student"]["student"]}
MAPPINGS['simd'] = {'simd':MAPPINGS["student"]["student"]}
MAPPINGS['progression'] = {'progression':MAPPINGS["student"]["student"]}
MAPPINGS['uninote'] = {'uninote':MAPPINGS["student"]["student"]}
MAPPINGS['archive'] = {'archive':MAPPINGS["student"]["student"]}
MAPPINGS['schoolsubject'] = {'schoolsubject':MAPPINGS["student"]["student"]}
MAPPINGS['schoollevel'] = {'schoollevel':MAPPINGS["student"]["student"]}
MAPPINGS['postschoollevel'] = {'postschoollevel':MAPPINGS["student"]["student"]}

