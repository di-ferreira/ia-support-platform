# Baseline da suíte — 2026-11-09 (antes da Fase 1)

Comando: `pytest tests/ -q -p no:cacheprovider`

## Resultado

- Total: 67 passed, 0 failed, 0 skipped
- Duração: 9.67s

## Contagem por arquivo

| Arquivo | Casos |
|---|---:|
| tests/test_api.py | 18 |
| tests/test_schemas.py | 13 |
| tests/test_ai_pipeline.py | 12 |
| tests/test_webhooks.py | 8 |
| tests/test_chat_service.py | 6 |
| tests/test_config.py | 4 |
| tests/test_appwrite_schema.py | 4 |
| tests/test_security.py | 1 |
| tests/test_cors.py | 1 |

## Falhas preexistentes

nenhuma

## Interpretação

Qualquer falha listada acima **não** é regressão de uma task do plano.
Uma task que introduza falha nova deve ser corrigida antes do commit.
