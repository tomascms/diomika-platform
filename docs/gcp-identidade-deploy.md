# Identidade GCP para o workflow `deploy-api.yml`

Valores reais (não são segredos): projecto `diomika` (n.º 123456789012), VM `diomika-api`,
zona `us-west1-a`, repositório `tomascms/diomika`, código na VM em `/home/deploy/diomika`.

Tudo isto é **[CONTAS]**: cria uma conta de serviço e uma federação de identidade. Não mexe na VM.
Sem chaves JSON: o GitHub autentica-se por OIDC (Workload Identity Federation, grátis).

```bash
P=diomika
N=123456789012
SA=github-deploy@$P.iam.gserviceaccount.com

gcloud services enable iap.googleapis.com sts.googleapis.com iamcredentials.googleapis.com --project=$P

gcloud iam service-accounts create github-deploy --project=$P --display-name="GitHub deploy API"
for r in roles/compute.instanceAdmin.v1 roles/iap.tunnelResourceAccessor; do
  gcloud projects add-iam-policy-binding $P --member="serviceAccount:$SA" --role=$r --condition=None
done
gcloud iam service-accounts add-iam-policy-binding 123456789012-compute@developer.gserviceaccount.com \
  --project=$P --member="serviceAccount:$SA" --role=roles/iam.serviceAccountUser

gcloud iam workload-identity-pools create github --project=$P --location=global
gcloud iam workload-identity-pools providers create-oidc diomika --project=$P --location=global \
  --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='tomascms/diomika' && assertion.ref=='refs/heads/main'"
gcloud iam service-accounts add-iam-policy-binding $SA --project=$P --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$N/locations/global/workloadIdentityPools/github/attribute.repository/tomascms/diomika"

# SSH só pelo IAP (o workflow usa --tunnel-through-iap)
gcloud compute firewall-rules create allow-ssh-iap --project=$P --network=default \
  --direction=INGRESS --allow=tcp:22 --source-ranges=35.235.240.0/20
```

No GitHub (ambiente `production`):

```bash
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER -e production --body "projects/123456789012/locations/global/workloadIdentityPools/github/providers/diomika"
gh secret set GCP_SERVICE_ACCOUNT -e production --body "github-deploy@diomika.iam.gserviceaccount.com"
gh variable set GCP_PROJECT -e production --body diomika
gh variable set GCP_ZONE -e production --body us-west1-a
gh variable set GCP_VM_NAME -e production --body diomika-api
gh variable set VM_APP_DIR -e production --body /home/deploy/diomika
```

A condição do provider só aceita a branch `main` deste repositório.

## Firewall — feito a 2026-10-21
Hoje SSH (22) e RDP (3389) estão abertos a `0.0.0.0/0`. A VM não precisa de portas de entrada
(o tráfego público chega pelo Cloudflare Tunnel). Fechar:

```bash
gcloud compute firewall-rules delete default-allow-rdp default-allow-ssh --project=diomika
```

Feito: SSH directo do PC deixou de funcionar; os scripts usam `deploy/vm_access.py`. Usar
`gcloud compute ssh diomika-api --zone us-west1-a --project diomika --tunnel-through-iap`.
Reversível recriando as regras.
