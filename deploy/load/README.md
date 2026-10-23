# Load & benchmark

| Script | Uso |
|--------|-----|
| `load_test.py` | Python — latência sob carga |
| `benchmark_api.py` | p50/p95 rápido antes/depois |
| `k6_stress.js` | k6 moderado (~10 VUs) |
| `k6_stress_heavy.js` | k6 pesado (100 VUs + burst) |

```powershell
python deploy/load/benchmark_api.py -n 15
python deploy/load/load_test.py --url https://api.diomika.com --concurrency 8 --requests 40
k6 run deploy/load/k6_stress.js
k6 run deploy/load/k6_stress_heavy.js
```
