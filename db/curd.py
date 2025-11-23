from pymongo.mongo_client import MongoClient



def insert_table(table: dict):
    collection.insert_one(table)

def get_table(table_id: str):
    return collection.find_one({"_id": table_id})

def update_table(table_id: str, table: dict):
    collection.update_one({"_id": table_id}, {"$set": table})
    
def delete_table(table_id: str):
    collection.delete_one({"_id": table_id})

def get_all_tables(collection):
    return list(collection.find())


def check_connection(mongo_client):
    try:
        mongo_client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)



def main():
    PASSWORD = ""
    URI = f"mongodb+srv://TableMagnifier:{PASSWORD}@tablemagnifier.gf5mkkc.mongodb.net/?appName=TableMagnifier"
    mongo_client = MongoClient(
        URI,
        tls=True,
        tlsAllowInvalidCertificates=True
    )

    # check_connection(mongo_client)

    print(mongo_client.list_database_names())
    
    # Database 선택 (없어도 선택 가능)
    db = mongo_client['TableInformation']

    # Collection 선택
    # Academic, Business, Example, Finance, Insurance, Medical, Public

    # TEST DATA INSERT
    collection = db['Example']
    collection.insert_one({
        "OriginPDFPath": "test.pdf",
        "OriginIMGPath": "test.png",
        "Prompt": {"Image_to_Markdown": "test", "Information": "test"},
        "QA": {"EvaluationCategoryName": {"Question": "test", "Answer": "test"}},
        "Markdown": "test"
    })
    print(get_all_tables(collection))


if __name__ == "__main__":
    main()
