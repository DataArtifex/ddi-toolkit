

**all classes**
```
PREFIX ucmis: <tag:ddialliance.org,2024:ucmis:>
select ?s where {
    ?s a ucmis:Class.
} 
order by ?s
```

**top classes**
```
PREFIX ucmis: <tag:ddialliance.org,2024:ucmis:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
select ?s where {
    ?s a ucmis:Class.
    FILTER NOT EXISTS { ?s rdfs:subClassOf ?any. }
} 
order by ?s
```

**class properties**
```
```
PREFIX cdi: <http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/>
select ?p ?o where {
    cdi:Concept ?p ?o.
}
order by ?p
```
