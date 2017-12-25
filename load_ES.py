'''
svakulenko
7 Aug 2017

Get (graph) data from Lucene (ES)
'''
import json

from elasticsearch import Elasticsearch


INDEX_LOCAL = 'data_gv_at'
INDEX_SERVER = 'odexploration'
INDEX_CSV = 'autcsv'

INDEX = INDEX_SERVER

N = 2914
N_DOCS = 2028

FIELDS = {
    "dataset_id": "raw.id",
    "title": "raw.title",
    "license": "raw.license_id",
    "categorization": "raw.categorization",
    "tags": "raw.tags.name",
    "organization": "raw.organization.name",
    "dataset_link": "dataset.dataset_link",
}


class ESClient():

    def __init__(self, index=INDEX, host='localhost', port=9200):
        self.es = Elasticsearch(hosts=[{"host": host, "port": port}])
        self.index = index

    def check_n_items(self):
        res = self.es.search(index=self.index, body={"query": {"match_all": {}}})
        print("Total: %d items" % res['hits']['total'])

    def show_one(self):
        result = self.es.search(index=self.index, body={"query": {"match_all": {}}})['hits']['hits'][0]
        print json.dumps(result, indent=4, sort_keys=True)

    def search(self, keywords, limit=N):
        result = self.es.search(index=self.index, size=limit, body={"query": {"match": {"_all": keywords}}})['hits']['hits']
        return result

    def sample_subset(self, keywords, facet_in, entity, limit=2):
        query = [{"match": {FIELDS[facet_in]: entity}}]
        if keywords:
            query.append({"match": {"_all": keywords}})
        result = self.es.search(index=self.index, size=limit,
            body={"query": {"bool": {"must": query}}})['hits']['hits']
        return result

    def describe_subset(self, keywords=None, top_n=N, limit=N):
        '''
        get stats for the search subsample of the information space
        '''
        if keywords:
            query = {"match": {"_all": keywords}}
        else:
            {"match_all": {}}
        result = self.es.search(index=self.index, explain=True, size=limit, body={"query": query, "aggs": {
                "title": {"terms": {"field": "raw.title.keyword", "size" : top_n}},
                "license": {"terms": {"field": "raw.license_id.keyword", "size" : top_n}},
                "categorization": {"terms": {"field": "raw.categorization.keyword", "size" : top_n}},
                "tags": {"terms": {"field": "raw.tags.name.keyword", "size" : top_n}},
                "organization": {"terms": {"field": "raw.organization.name.keyword", "size" : top_n}}
            }})
        return result  #['aggregations']

    def aggregate_entity(self, facet, value, top_n=N, limit=N):
        field = FIELDS[facet]
        facets = {
                "title": {"terms": {"field": "raw.title.keyword", "size" : top_n}},
                "license": {"terms": {"field": "raw.license_id.keyword", "size" : top_n}},
                "categorization": {"terms": {"field": "raw.categorization.keyword", "size" : top_n}},
                "tags": {"terms": {"field": "raw.tags.name.keyword", "size" : top_n}},
                "organization": {"terms": {"field": "raw.organization.name.keyword", "size" : top_n}}
                }
        facets.pop(facet, None)
        result = self.es.search(index=self.index, size=limit, q='%s="%s"'%(field, value), body={"aggs": facets})
        return result['aggregations']

    def search_by(self, facet, value, limit=N):
        field = FIELDS[facet]
        result = self.es.search(index=self.index, size=limit, q='%s="%s"'%(field, value))['hits']['hits']
        return result

    def top(self, n=N):
        '''
        returns n most popular entities
        '''
        result = self.es.search(index=self.index, body={"query": {"match_all": {}}, "aggs": {
                "title": {"terms": {"field": "raw.title.keyword", "size" : n}},
                "license": {"terms": {"field": "raw.license_id.keyword", "size" : n}},
                "categorization": {"terms": {"field": "raw.categorization.keyword", "size" : n}},
                "tags": {"terms": {"field": "raw.tags.name.keyword", "size" : n}},
                "organization": {"terms": {"field": "raw.organization.name.keyword", "size" : n}}
            }})
        return result['aggregations']

    def count(self):
        '''
        returns cardinality (number of entities for each of the attributes)
        '''
        result = self.es.search(index=self.index, body={"query": {"match_all": {}}, "aggs": {
                "licenses": {"cardinality": {"field": "raw.license_id.keyword"}},
                "categories": {"cardinality": {"field": "raw.categorization.keyword"}},
                "tags": {"cardinality": {"field": "raw.tags.name.keyword"}},
                "organizations": {"cardinality": {"field": "raw.organization.name.keyword"}}
            }})
        return result['aggregations']


def test_index(index=INDEX):
    db = ESClient(index)
    db.check_n_items()
    # db.show_one()


def test_aggregation_stats(index=INDEX):
    db = ESClient(index)
    print db.top()
    # print db.count()


def test_describe_subset(index=INDEX, top_n=2):
    db = ESClient(index)
    keyword = "I would like to know more about finanzen"
    results = db.describe_subset(keywords=keyword, top_n=top_n)['aggregations']
    print json.dumps(results, indent=4, sort_keys=True)
    # pick the most representative documents from the subset


def test_top_docs_search(index=INDEX, top_n=2, n_samples=5):
    db = ESClient(index)
    keyword = "stadt wien"
    results = db.describe_subset(keywords=keyword, top_n=top_n)
    # show the top docs
    for item in results['hits']['hits'][:n_samples]:
        print item['_source']['raw']['title']


def test_search(index=INDEX, n_samples=5):
    db = ESClient(index)
    results = db.search("finanzen")
    for result in results[:n_samples]:
        print result['_source']['raw']['categorization']
        print result['_source']['raw']['title']
    print len(results), "results"


def test_search_csv():
    dataset_link = "http://www.data.gv.at/katalog/dataset/80607cc6-8fc1-4b2e-8517-716de8f1ba63"
    print dataset_link
    csv_db = ESClient(INDEX_CSV, host='csvengine', port=9201)
    # csv_db.show_one()
    tables = csv_db.search_by(facet='dataset_link', value=dataset_link)
    if tables:
        print tables[0]['_source']['no_rows'], 'rows'


if __name__ == '__main__':
    test_search_csv()
