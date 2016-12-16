CREATE DATABASE IF NOT EXISTS whoogle;
USE whoogle;
DROP TABLE Maps CASCADE;

CREATE TABLE Maps (
handle_id varchar(255) UNIQUE,
mapdata LONGBLOB,
date_of_creation date,
CONSTRAINT handle_id_pk PRIMARY KEY (handle_id)
)