## Security checklist (obrigatório em PRs que tocam backend/API)

- [ ] Novas rotas `/admin` ou `/system` têm `Depends(admin_must_be_local)` + `require_*`
- [ ] Não adicionar `ADMIN_ALLOW_REMOTE` nem bypass de MFA
- [ ] Sem secrets no código / sem `VITE_` com service keys
- [ ] Uploads passam por `validate_upload_bytes`
- [ ] Fetch URL externo usa `core.ssrf_guard.assert_safe_outbound_url`
- [ ] Correu localmente: `python deploy/security_gate.py`
- [ ] Testes: `python -m pytest backend-api/tests -q`

## Summary

<!-- O que muda e porquê -->

## Test plan

- [ ] `python deploy/security_gate.py`
- [ ] `python -m pytest backend-api/tests -q`
