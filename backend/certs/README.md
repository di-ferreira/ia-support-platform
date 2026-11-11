# Bundle de CAs — API de chamados Emsoft (spec 11)

`emsoft-ca-bundle.pem` é o store de CAs usado pelo backend para verificar o
TLS de `https://emsoft.ddns.net/portal-api` (config `EMSOFT_CHAMADOS_CA_BUNDLE`,
padrão `/app/certs/emsoft-ca-bundle.pem`). Não contém segredo: é dado público
de autoridades certificadoras, commitável.

## Por que existe

O servidor emite certificado Let's Encrypt assinado pela intermediária
**YR2** (geração Y). Em 2026-11-11, o store de CAs do host (146 certificados)
não continha nem a YR2 nem a raiz **ISRG Root YR** — conexões com
`sslverify=True` falhavam com `CERTIFICATE_VERIFY_FAILED`. Em vez de
desabilitar a verificação (proibido em produção, spec 11 §TLS, linha 185),
montamos este bundle.

Cadeia completa:

1. Folha `CN=emsoft.ddns.net` (apresentada pelo servidor, emissor YR2)
2. `O = Let's Encrypt, CN = YR2` (2025–2028)
3. `O = ISRG, CN = Root YR` (autoassinada, 2025–2045)

## Composição

- Store de CAs do host (Mozilla root store, snapshot de 2026-11-11,
  146 certificados)
- Let's Encrypt YR2
- ISRG Root YR

Total: 148 certificados PEM.

## Como atualizar

O bundle é um snapshot: quando a YR2 ou a raiz caducarem (2028), ou quando o
servidor migrar de CA, regenerar:

```bash
# 1. Store base do host (ajustar ao sistema real)
cat /etc/ssl/certs/ca-certificates.crt > bundle.pem

# 2. Intermediária e raiz Let's Encrypt geração Y (nomes atuais em
#    https://letsencrypt.org/certs/; os URLs antigos retornam 404)
curl -fsS https://letsencrypt.org/certs/yr.pem >> bundle.pem
curl -fsS https://letsencrypt.org/certs/gen-y/root-yr.pem >> bundle.pem

# 3. Verificar a cadeia contra o servidor
openssl verify -CAfile bundle.pem \
  <(openssl s_client -connect emsoft.ddns.net:443 -servername emsoft.ddns.net \
     </dev/null 2>/dev/null | openssl x509)
```

Depois copiar para `backend/certs/emsoft-ca-bundle.pem` e commitar.

## Evidência da sonda (2026-11-11)

- `httpx` com este bundle → `GET /v1/chamados` HTTP 200,
  `success=true`, `totalRegistros=1155`
- `httpx` com o store do sistema → `CERTIFICATE_VERIFY_FAILED`
- `openssl verify -CAfile bundle.pem` → OK
