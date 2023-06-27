import sys
import pandas as pd
from typing import List, Dict
from SPARQLWrapper import SPARQLWrapper, JSON
import py2neo
from py2neo import Graph
from py2neo.data import Node, Relationship, Subgraph
from tqdm import tqdm
from datetime import datetime

query = '''SELECT Distinct ?artist ?getty_union_id ?artistLabel (group_concat( distinct ?birth_place; separator=", ") AS ?countries) ?birth_date ?death_date (group_concat(?movement; separator=", ") AS ?movements)
WHERE
{
  ?artist wdt:P245 ?getty_union_id.
  OPTIONAL {?artist wdt:P135 ?movement.
  ?movement  wdt:P31 wd:Q968159.}
  OPTIONAL {?artist wdt:P27 ?birth_place.}
  OPTIONAL {?artist wdt:P569 ?birth_date.}
  OPTIONAL {?artist wdt:P570 ?death_date.}
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en". 
    ?artist rdfs:label ?artistLabel . 
  }
} group by ?artist ?getty_union_id ?artistLabel ?birth_date ?death_date'''

query_countries = '''SELECT Distinct ?country ?countryLabel
WHERE
{
  ?country wdt:P31 wd:Q3624078.
  SERVICE wikibase:label {bd:serviceParam wikibase:language "en". }
}'''

query_movements = '''SELECT ?movement ?movementLabel (group_concat(?start_time; separator=", ") AS ?start_dates) (group_concat(?end_time; separator=", ") AS ?end_dates) (group_concat(?anterior; separator=", ") AS ?previous_movements) (group_concat(?siguiente; separator=", ") AS ?next_movements)
WHERE
{
  ?movement p:P31/ps:P31/wdt:P279* wd:Q968159.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  OPTIONAL {?movement wdt:P580 ?start_time}
  OPTIONAL {?movement wdt:P582 ?end_time}
  OPTIONAL {?movement wdt:P155 ?anterior}
  OPTIONAL {?movement wdt:P156 ?siguiente}
} group by ?movement ?movementLabel'''

query_teachers = '''SELECT Distinct ?artist ?teacher
WHERE
{
  ?artist wdt:P245 ?getty_union_id.
  ?artist wdt:P1066 ?teacher.
  ?teacher wdt:P245 ?teacher_id.
}'''

query_students = '''SELECT Distinct ?artist ?student
WHERE
{
?artist wdt:P245 ?getty_union_id.
?artist wdt:P802 ?student.
?student wdt:P245 ?student_id.
}'''

query_influences = '''SELECT Distinct ?artist ?influence
WHERE
{
  ?artist wdt:P245 ?getty_union_id.
  ?artist wdt:P737 ?influence.
  ?influence wdt:P245 ?influence_id.
}'''


class WikiDataQueryResults:
    #A class that can be used to query data from Wikidata using SPARQL and return the results as a Pandas DataFrame or a list of values for a specific key.

    def __init__(self):
        #Initializes the WikiDataQueryResults object with a SPARQL query string.
        #:param query: A SPARQL query string.

        self.user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
        self.endpoint_url = "https://query.wikidata.org/sparql"
        
        print("Querying wikidata for artistic movements...")
        self.sparql_movements = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql_movements.setQuery(query_movements)
        self.sparql_movements.setReturnFormat(JSON)
        print("Querying wikidata for countries...")
        self.sparql_countries = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql_countries.setQuery(query_countries)
        self.sparql_countries.setReturnFormat(JSON)
        print("Querying wikidata for artist...")
        self.sparql = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)
        print("Querying wikidata for artist's students...")
        self.sparql_students = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql_students.setQuery(query_students)
        self.sparql_students.setReturnFormat(JSON)
        print("Querying wikidata for artist's teachers...")
        self.sparql_teachers = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql_teachers.setQuery(query_teachers)
        self.sparql_teachers.setReturnFormat(JSON)
        print("Querying wikidata for artist's influences...")
        self.sparql_influences = SPARQLWrapper(self.endpoint_url, agent=self.user_agent)
        self.sparql_influences.setQuery(query_influences)
        self.sparql_influences.setReturnFormat(JSON)

    def __transform2dicts(self, results: List[Dict]) -> List[Dict]:
        #Helper function to transform SPARQL query results into a list of dictionaries.
        #:param results: A list of query results returned by SPARQLWrapper.
        #:return: A list of dictionaries, where each dictionary represents a result row and has keys corresponding to the variables in the SPARQL SELECT clause.

        new_results = []
        for result in results:
            new_result = {}
            for key in result:
                new_result[key] = result[key]['value']
            new_results.append(new_result)
        return new_results

    def _load(self, sparql: SPARQLWrapper) -> List[Dict]:
        #Helper function that loads the data from Wikidata using the SPARQLWrapper library, and transforms the results into a list of dictionaries.
        #:return: A list of dictionaries, where each dictionary represents a result row and has keys corresponding to the
        #variables in the SPARQL SELECT clause.
        
        results = sparql.queryAndConvert()['results']['bindings']
        results = self.__transform2dicts(results)
        return results

    def load_as_dataframe(self, sparql: SPARQLWrapper) -> pd.DataFrame:
        #Executes the SPARQL query and returns the results as a Pandas DataFrame.
        #:return: A Pandas DataFrame representing the query results.

        results = self._load(sparql)
        return pd.DataFrame.from_dict(results)
    

    def load_to_data_base(self) -> pd.DataFrame:
        #Gets the data from wikidata and creates creates the nodes and relationships
        #:return: None.

        dburl='bolt://localhost:7687/artists'
        user="scraper"
        pasw="Por-Favor-No-Me-Hackees-Es-Para-La-Facultad-2"

        graph = Graph(dburl, auth=(user, pasw))

        movements_df = self.load_as_dataframe(self.sparql_movements)

        print("Loading movements")
        nodes = []
        for index, row in tqdm(movements_df.iterrows(), total=movements_df.shape[0]):
            node = Node(
                'Movement',
                name=row['movementLabel'],
                wd_id=row['movement'],
                start_dates=row['start_dates'].split(", "),
                end_dates=row['end_dates'].split(", "),
            )
            nodes.append(node)
            graph.create(node)
        movements_df["node"] = nodes

        print("Loading relationships between movements")
        for index, row in tqdm(movements_df.iterrows(), total=movements_df.shape[0]):
            previous_movements = row['previous_movements'].split(", ") if row['previous_movements'] else []
            for prev_mov in previous_movements:
                if movements_df.index[movements_df['movement'] == prev_mov].any():
                    index = movements_df.index[movements_df['movement'] == prev_mov][0]
                    graph.create(Relationship(nodes[index], "next_movement", row["node"]))
            
            next_movements = row['next_movements'].split(", ") if row['next_movements'] else []
            for next_mov in next_movements:
                if movements_df.index[movements_df['movement'] == next_mov].any():
                    index = movements_df.index[movements_df['movement'] == next_mov][0]
                    graph.create(Relationship(row["node"], "next_movement", nodes[index]))            

        countries_df = self.load_as_dataframe(self.sparql_countries)
        dict_countries = {}
        for index, row in countries_df.iterrows():
            dict_countries[row["country"]] = row["countryLabel"]
            
        print("Loading artists")
        artists = self.load_as_dataframe(self.sparql)
        artists_nodes = []
        for index, row in tqdm(artists.iterrows(), total=artists.shape[0]):
            countries_list = list(filter(lambda c: c is not None, map(lambda c: dict_countries.get(c, None), row['countries'].split(", "))))
            try:
                birth_date = datetime.strptime(row["birth_date"], "%Y-%m-%dT%H:%M:%SZ") if isinstance(row["birth_date"], str) else None
            except ValueError:
                birth_date = None

            try:
                death_date = datetime.strptime(row["death_date"], "%Y-%m-%dT%H:%M:%SZ") if isinstance(row["death_date"], str) else None
            except ValueError:
                death_date = None

            node = Node(
                'Artist',
                artist=row['artist'],
                getty_union_id=row['getty_union_id'],
                name=row["artistLabel"],
                birth_date=birth_date,
                death_date=death_date,
                countries=countries_list if countries_list else ["None"]
            )
            artists_nodes.append(node)
            graph.create(node)
        artists["node"] = artists_nodes
        
        print("Loading relationships between artists and movements")
        for index, row in tqdm(artists.iterrows(), total=artists.shape[0]):
            movements = row['movements'].split(", ") if row['movements'] else []
            for mov in movements:
                if movements_df.index[movements_df['movement'] == mov].any():
                    index = movements_df.index[movements_df['movement'] == mov][0]
                    graph.create(Relationship(row["node"], "IS_IN", nodes[index]))


        print("Loading relationship IS_STUDENT_OF")
        teachers = self.load_as_dataframe(self.sparql_teachers)
        for index, row in tqdm(teachers.iterrows(), total=teachers.shape[0]):
            if artists.index[artists['artist'] == row["artist"]].any() and artists.index[artists['artist'] == row["teacher"]].any():
                index_artist = artists.index[artists['artist'] == row["artist"]][0]
                index_teacher = artists.index[artists['artist'] == row["teacher"]][0]
                graph.create(Relationship(artists_nodes[index_artist], "IS_STUDENT_OF", artists_nodes[index_teacher]))
        
        print("Loading relationship IS_TEACHER_OF")
        students = self.load_as_dataframe(self.sparql_students)
        for index, row in tqdm(students.iterrows(), total=students.shape[0]):
            if artists.index[artists['artist'] == row["artist"]].any() and artists.index[artists['artist'] == row["student"]].any():
                index_artist = artists.index[artists['artist'] == row["artist"]][0]
                index_student = artists.index[artists['artist'] == row["student"]][0]
                graph.create(Relationship(artists_nodes[index_artist], "IS_TEACHER_OF", artists_nodes[index_student]))
        
        print("Loading relationship INFLUENCED_BY")
        influences = self.load_as_dataframe(self.sparql_influences)
        for index, row in tqdm(influences.iterrows(), total=influences.shape[0]):
            if artists.index[artists['artist'] == row["artist"]].any() and artists.index[artists['artist'] == row["influence"]].any():
                index_artist = artists.index[artists['artist'] == row["artist"]][0]
                index_influence = artists.index[artists['artist'] == row["influence"]][0]
                graph.create(Relationship(artists_nodes[index_artist], "INFLUENCED_BY", artists_nodes[index_influence]))

        
        

        
        
            



def main():
    data_extracter = WikiDataQueryResults()
    data_extracter.load_to_data_base()

main()
