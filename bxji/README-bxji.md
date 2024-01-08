# 上手过程，解读 | bxji
### 准备

#### 依赖包安装 
```shell
conda install esri::sparqlwrapper

```

### 整体流程
#### 1.先将测试数据 kg_demo_movie-mysql8.0.sql 导入MySQL数据库中
#### 2.基于图谱需求，构建本体 ontology.ttl文件
#### 3.创建D2R的数据库到三元组映射文件
  ``` shell
   # /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
   # 生成映射文件
  ./generate-mapping -u root -p *** -o kg_movie.ttl jdbc:mysql://172.30.9.66:3306/spark_desk?useSSL=false
  ```
#### 4.修改  kg_movie.ttl 与 ontology.ttl 本休映射一致
 - 将默认的映射词汇改为我们本体中的词汇，对象名、属性名保持一致 
 - 删除不需要有属性如， lable
    ```
    # 新增如前缀, 原vocab:Genre可写为 :Genre
    @prefix : <http://www.kgdemo.com#> . 
    ```

#### 5.启动d2r-server，开启SparQL查询
``` shell
  # 这时可以 启动./d2r-server 加载修改过的三元组映射 kg_movie.ttl 文件
  # /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
  ./d2r-server kg_movie.ttl   # 启动D2R服务
 
  # 然后，打开 http://localhost:2020 ，可以进行SparQL 查询了
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

### 三、Fuseki与OWL推理实战
#### 6.将数据库中的数据转为RDF存储文件

```shell
# /iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1
./dump-rdf -o kg_movie.nt ./kg_movie.ttl
```

#### 使用jena-TDB数据库存储三元组的nt转储文件 
```shell
export JAVA_HOME=/iflytek/java/jdk_11 
export PATH=$JAVA_HOME/bin:$PATH
mdkr tdb2
cd  /iflytek/bxji/jena/jena
./bin/tdbloader   --loc="./tdb2"  "/iflytek/bxji/d2rq-0.8.1/d2rq-0.8.1/kg_movie.nt"

```

#### 配置fuseki
```shell# 
export JAVA_HOME=/iflytek/java/jdk_11 
export PATH=$JAVA_HOME/bin:$PATH
cd /iflytek/bxji/jena/fuseki
# 初始化，运行 “fuseki-server”后退出，会自动创建“run”文件夹
./bin/fuseki-server
```
然后， 将我们的本体文件“ontology.owl”移动到“run”文件夹下的“databases”文件夹中，并将“owl”后缀名改为“ttl”。
在“run”文件夹下的“configuration”中，我们创建名为“fuseki_conf.ttl”的文本文件（取名没有要求），加入如下内容：
```
# 开启jena-Fuseki服务，就可以SparQL查询了
./bin/fuseki-server --loc="./fuseki" --update --db="/iflytek/bxji/jena/jena/tdb2"
./bin/fuseki-server --loc=/iflytek/bxji/jena/jena/tdb2 /kg_demo_movie

Fuseki默认的端口是3030，浏览器访问“http://localhost:3030/

PREFIX : <http://www.kgdemo.com#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT * WHERE {
?x :movieTitle '功夫'.
?x ?p ?o.
}
```
