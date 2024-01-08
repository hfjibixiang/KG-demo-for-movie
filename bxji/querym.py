from SPARQLWrapper import SPARQLWrapper, JSON

if __name__ == '__main__':
    sparql = SPARQLWrapper("http://172.31.185.103:2020/sparql")
    sparql.setQuery("""
        PREFIX kgdemo: <http://www.kgdemo.com#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?n WHERE {
          ?s rdf:type kgdemo:Person.
          ?s kgdemo:personName '巩俐'.
          ?s kgdemo:hasActedIn ?o.
          ?o kgdemo:movieTitle ?n.
          ?o kgdemo:movieRating ?r.
        FILTER (?r >= 7)
        }
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    for result in results["results"]["bindings"]:
        print(result["n"]["value"])



