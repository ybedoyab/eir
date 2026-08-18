#!/usr/bin/env bash
# One-time bootstrap for Terraform remote state. Run with owner/editor credentials.
set -euo pipefail

PROJECT="${PROJECT:-eir-ata}"
PROJECT_NUMBER="${PROJECT_NUMBER:-658898892127}"
BUCKET="eir-ata-terraform-state-${PROJECT_NUMBER}"
REGION="${REGION:-us-central1}"

echo "Bootstrapping Terraform state bucket: ${BUCKET}"

if ! gcloud storage buckets describe "gs://${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --public-access-prevention
fi

gcloud storage buckets update "gs://${BUCKET}" --versioning

echo "Bucket ready. Next:"
echo "  cd infra/terraform"
echo "  terraform init"
echo "  terraform import ...  # see README.md"
echo "  terraform plan"
