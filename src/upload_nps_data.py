# MongoDB has a 500 collection limit for free version

SURVEY_NAMES = ['Survey1']

import pandas as pd
import os
import pymongo
import sys
import json
    
creds = {
    "User":"nps_owner",
    "Password":"owner_pwd_123",
    "Cluster":"NPSCluster",
    "Fields":"['Score', 'Review', 'Date']"
}

atlas_conn_str = f"mongodb+srv://{creds['User']}:{creds['Password']}@{creds['Cluster']}.gu6rrz5.mongodb.net/?retryWrites=true&w=majority"
survey_fields = eval(creds['Fields'])

try:
    client = pymongo.MongoClient(atlas_conn_str)
except pymongo.errors.ConfigurationError:
    print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
    sys.exit(1)

NPSResponsesDB = client.NPSResponsesDB 
print('MongoDB Connected')

for survey in SURVEY_NAMES:

    survey_collection = NPSResponsesDB[survey]
    survey_df = pd.read_csv(survey + '.csv')[survey_fields]
    survey_response_docs = survey_df.to_dict('records')
    
    try: 
        result = survey_collection.insert_many(survey_response_docs)
    except pymongo.errors.OperationFailure:
        print("An authentication error was received. Are you sure your database user is authorized to perform write operations?")
        sys.exit(1)
    else:
        inserted_count = len(result.inserted_ids)
        print(f"Inserted {inserted_count} documents from {survey}")

print("\n Upload to NPSResponsesDB Complete")