savedcmd_certs/signing_key.pem := openssl req -new -nodes -utf8 -sha512 -days 36500 -batch -x509 -config certs/x509.genkey -outform PEM -out certs/signing_key.pem -keyout certs/signing_key.pem -newkey ec -pkeyopt ec_paramgen_curve:secp384r1 2>&1
