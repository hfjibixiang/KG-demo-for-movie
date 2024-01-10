# 上手过程，解读 | Benji
### 一、本体建模与数据准备
- 基于业务需求，构建知识图谱本体 ontology.ttl 文件；
  - 使用的工具[protégé]构建本体，文件格式为 OWL/XML Syntax
  - 修改 本体IRI配置`@base <http://www.kgdemo.com> `为自己的路径

- 数据准备，将测试数据 kg_demo_movie-mysql8.0.sql 导入MySQL数据库中
  - 实体间关联一定要创建表的外键约束；
  - 多对多（m:n）关联的中间表一定要创建复合主键约束；

### 二、关系数据转换为RDF数据
- 使用D2RQ，生成从数据库到RDF三元组映射文件 kg_movie.ttl
  ```shell
  # /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
  # 生成映射文件
  ./generate-mapping -u root -p *** -o kg_movie.ttl jdbc:mysql://172.30.9.66:3306/spark_desk?useSSL=false
  ```

- 修改 kg_movie.ttl 映射文件，保持与构建的本休一致
  - 将默认的映射词汇改成与本体中的词汇一致，如：对象名、关系名、属性名 
  - 删除不需要有属性如， lable
  - 新增 `@prefix : <http://www.kgdemo.com#> .` 前缀楝配置，这样文中 `vocab:Genre` 可写为` :Genre`

-  将数据导出为RDF三元组文件
  - ` kg_movi.ttl`是修改后的mapping文件。
  - 支持导出的RDF格式有“TURTLE”, “RDF/XML”, “RDF/XML-ABBREV”, “N3”, 和“N-TRIPLE”。“N-TRIPLE”是默认的输出格式。
    ``` shell
    # cd  /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
    ./dump-rdf  -o  kg_demo_movie.nt     ./kg_movie.ttl
    ```

### 三、启用D2RQ的SPARQL查询端点
D2RQ，是以虚拟RDF的方式来访问关系数据库中的数据，把SPARQL查询，按照mapping文件，翻译成SQL语句完成最终的查询，然后把结果返回给用户。两个缺点：1）不支持直接将RDF数据通过endpoint发布到网络上。2）不支持推理。

> - 在访问频率不高，数据变动频繁的场景下，这种方式比较合适。
> - 对于访问频率比较高的场景（比如KBQA），将数据转为RDF再提供服务更为合适。

#### 1.  SparQL 查询服务

- 进入d2rq目录，命令启动D2R Server
  ```shell
   # 这时可以 启动./d2r-server 加载修改过的三元组映射 kg_movie.ttl 文件
    # /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
    ./d2r-server kg_movie.ttl   # 启动D2R服务
  ```

- 然后，打开 http://localhost:2020 ，可以进行SparQL 查询了
  ```shell
    # 周星驰出演了哪些电影？
    SELECT DISTINCT ?n WHERE {
    ?s rdf:type :Person.
    ?s :personName '周星驰'.
    ?s :hasActedIn ?o.
    ?o :movieTitle ?n
     }    LIMIT 100
     
    # “英雄这部电影有哪些演员参演？”
     SELECT DISTINCT ?n WHERE {
       ?s rdf:type :Movie.
       ?s :movieTitle  '英雄'.
       ?a :hasActedIn ?s.
       ?a :personName ?n
     }    LIMIT 100
  ```

- 编写Python脚本，利用D2RQ开启SPARQL endpoint服务端点进行查询 `sparqk-query.py`

  ```python
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
  ```

### 四、jena 查询及推理

- Apache Jena 是开源的Java语义网框架，**用于构建 语义网和链接数据应用**。
  - TDB 是Jena用于存储RDF的组件
  
  - Jena 提供了RDFS、OWL和通用规则推理机，*[其实Jena的RDFS和OWL推理机也是通过Jena自身的通用规则推理机实现的。]*

  - Fuseki是Jena提供的SPARQL服务器
  
#### 1.三元组TDB存储

- 将RDF数据转储文件，导入TDB数据库 

    先将结构化数据导出为RDF三元组文件：
    ```shell
    # cd  /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1 
    ./dump-rdf  -o  kg_demo_movie.nt     ./kg_movie.ttl  #将数据库中的数据转为RDF存储文件
    ```

- 将三元组文件，加载到TDB数据库中
    ```shell
    export JAVA_HOME=/iflytek/java/jdk_11 
    export PATH=$JAVA_HOME/bin:$PATH
    cd  /iflytek/bxji/jena/jena
    ./bin/tdbloader   --loc="./tdb2"  "/iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1/kg_movie.nt" 
    # --loc”指定tdb存储的位置， 这时，当前路径会创建一个tdb2目录
    ```

- 初始化 jena-fuseki 服务
  进入`apache-jena-fuseki-X.X.X`文件夹，运行`useki-server`，然后退出，程序会为在当前目录自动创建“run”文件夹。

  ```shell 
  export JAVA_HOME=/iflytek/java/jdk_11 
  export PATH=$JAVA_HOME/bin:$PATH
  cd /iflytek/bxji/jena/fuseki
  # 初始化，运行 “fuseki-server”后退出，会自动创建“run”文件夹
  ./bin/fuseki-server
  ```

#### 1. 基于本体推理
> 配置 fuseki  OWL 推理机，再次运行 fuseki-server 
- 将本体文件 `ontology.owl` 移动到 `./run/databases` 文件夹中，后缀名改为 `ontology.ttl`
- 在 `./run/configuration` 中，创建名为 `fuseki_conf.ttl`的文本文件（取名没有要求），加入如下
```properties
# 详细内容请参考 fuseki_conf.ttl 原文件，# 重点配置如下：
    # 本体文件的路径
    ja:content [ja:externalContent <file:///iflytek/bxji/jena-4.10/apache-jena-fuseki-4.10.0/run/databases/ontology.ttl> ] ;

    # 开户OWL推理机 【同时只能启用一个推理机】
    ja:reasoner [ja:reasonerURL <http://jena.hpl.hp.com/2003/OWLFBRuleReasoner>] .

    # 关闭规则推理机，并指定规则文件路径 【同时只能启用一个推理机】
    #ja:reasoner [
    #    ja:reasonerURL <http://jena.hpl.hp.com/2003/GenericRuleReasoner> ;
    #    ja:rulesFrom <file:rules.ttl> ; ]
    #.

# 配置 TDB 数据库存储路径， 这是真实存在于tdb2中的数据（有别于D2RQ）
<#tdbDataset> rdf:type tdb:DatasetTDB ;
    tdb:location "/iflytek/bxji/jena/jena/tdb2" ;
    .
```

再次运行 ./bin/fuseki-server服务 ，浏览器访问“http://localhost:3030/”和之前介绍的D2RQ web界面类似，我们可以进行SPARQL查询等操作。

- 编写Python脚本，SPARQL endpoint服务端点进行查询
在Python中用SPARQLWrapper向Fuseki server发送查询请求，电影的“hasActor”属性可以通过OWL推理机得到的（原本的RDF数据里面是没有）。

```python
PREFIX : <http://www.kgdemo.com#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT * WHERE {
?x :movieTitle '功夫'.
?x ?p ?o.
}

# 
```

#### 2.基于规则推理
- 在“databases”文件夹下新建一个规则文件“rules.ttl”
  ```properties
  # 统一本体前缀
  @prefix : <http://www.kgdemo.com#> .  
  @prefix owl: <http://www.w3.org/2002/07/owl#> .
  @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
  @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  # 意思是：如果有一个演员，出演了一部喜剧电影，那么他就是一位喜剧演员。
  [ruleComedian: (?p :hasActedIn ?m) (?m :hasGenre ?g) (?g :genreName '喜剧') -> (?p rdf:type :Comedian)]
  [ruleInverse: (?p :hasActedIn ?m) -> (?m :hasActor ?p)]
  ```

- 修改配置文件“fuseki_conf.ttl”,关闭OWL推理机，开启规则推理机，并指定规则文件路径
  > 我们只能启用一种推理机。但OWL的推理功能也可以在规则推理机里面实现
  >
  > 因此，这里定义了“ruleInverse”来表示“hasActedIn”和“hasActor”的相反关系。更多细节读者可以参考文档。
  
  ```properties
   #本体文件的路径
      ja:content [ja:externalContent <file:///D:/apache%20jena/apache-jena-fuseki-3.5.0/run/databases/ontology.ttl> ] ;
      
      #关闭OWL推理机
      #ja:reasoner [ja:reasonerURL <http://jena.hpl.hp.com/2003/OWLFBRuleReasoner>] .
  
      #开启规则推理机，并指定规则文件路径
      ja:reasoner [
          ja:reasonerURL <http://jena.hpl.hp.com/2003/GenericRuleReasoner> ; 
          ja:rulesFrom <file:///D:/apache%20jena/apache-jena-fuseki-3.5.0/run/databases/rules.ttl> ; ]
      .
  ```
  
  
  
- 

  

 依赖包安装 

```shell
conda install esri::sparqlwrapper
```
