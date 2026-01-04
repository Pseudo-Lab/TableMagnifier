# mongoDB CRUD 기능 구현

import pymongo
from pymongo import MongoClient

def mongo_client(PASSWORD, collection_name):
    URI = f"mongodb+srv://TableMagnifier:{PASSWORD}@tablemagnifier.gf5mkkc.mongodb.net/?appName=TableMagnifier"
    mongo_client = MongoClient(
        URI,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    
    # Database 선택
    db = mongo_client['TableInformation']
    # Collection 선택 : Academic, Business, Finance, Insurance, Medical, Public
    collection = db[f'{collection_name}']
    return collection


def read_table(collection, Search_query):
    tables = collection.find(Search_query)
    return tables


def update_table(collection, table_name):
    Search_query = {"Domain": "Example", "ImageFileName": "E_table_0_1.png"}
    tables = read_table(collection, Search_query) # 여러개 조회 가능
    # 1개만 단일로 조회하고 싶다면 collection.find_one(Search_query)
    for table in tables:
        # 단일 Table에 대해 검색하기 위해 그대로 검색 Query로 사용
        single_search_query = dict(table)
        table["HTMLText"] = "<test></test>" # 예시 함수 작성
        # 업데이트 할 정보 작성
        collection.update_one(single_search_query, {"$set": table})


if __name__ == "__main__":
    PASSWORD = ""
    collection = mongo_client(PASSWORD, "Example")
    update_table(collection, "Example")