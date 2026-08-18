terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.14"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.14"
    }
  }

  backend "gcs" {
    bucket = "eir-ata-terraform-state-658898892127"
    prefix = "eir"
  }
}
