# artists_db
Script and dump to fill a neo4j database with artists, movements and relationships betweens thems.

# Cloning instructions
Clone the repository as always but add the option --recursive to clone [Neovis.js](https://github.com/neo4j-contrib/neovis.js?) too

# Instructive to use script.py
1. install all pip requirements especified in requirements 
2. set the variables inside sript.py dburl, user, pasw with the db url, the user and password to connect to the database.
3. make sure there is a palette.json file with an array full with hex colors 
4. run `python script.py`

## In case of failure
1. If the script fails with an error sayind movements_palette[index] out of range you have to, delete palette.json run palette.py again but with the range used inside the for to something grater (wikidata keeps adding art movements)
2. if there is an error when fetching the artists you will have to clear the database (run the query `MATCH(n) DETACH DELETE n`) and re run the script.

# To use Neovis for visualizations.
1. build the neovis.js project in here as specified in their github https://github.com/neo4j-contrib/neovis.js?
2. go inside graphs.html and modify this values
```
neo4j: {
    serverUrl: "bolt://localhost:7687",
    serverUser: "user",
    serverPassword: "password"
}
```
3. open graph.html in any browser.

# Dump of the database
https://drive.google.com/file/d/1FiDuAp95SjBQzIjRe1L_jFMUD6ZVzZLW/view?usp=sharing

# Created by
## Team 25:
- Genaro Nadile
- Gabriel Corujo
