#!/bin/bash

IP="ВАШ ВНЕШНИЙ IP К КОТОРОМУ БУДУТ ПОДКЛЮЧАТЬСЯ КЛИЕНТЫ"
mkdir -p certs

openssl req -new -x509 -days 365 -nodes \
  -out "certs/${IP}.crt" \
  -keyout "certs/${IP}.key" \
  -subj "/C=US/ST=State/L=City/O=Org/CN=${IP}"

chmod 644 "certs/${IP}.key"