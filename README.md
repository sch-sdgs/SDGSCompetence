# SDGSCompetence

### Start mysql container

`docker run --name mysql -e MYSQL_ROOT_PASSWORD=stardb -p 3306:81 -d mysql:5.7`

### Start phpmyadmin container

`docker run --name myadmin -d --link mysql:db -p 80:82 phpmyadmin/phpmyadmin`


### Remove "ONLY_FULL_GROUP_BY"

