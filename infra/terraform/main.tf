terraform {
  required_providers {
    databricks = { source = "databricks/databricks", version = "~> 1.55" }
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

resource "databricks_job" "dlt_pipeline" {
  name = "customer360_dlt_dev"

  task {
    task_key = "run_dlt"
    notebook_task {
      notebook_path = "/Repos/${var.repo_path}/pipelines/dlt_pipeline.py"
    }
    existing_cluster_id = var.cluster_id
  }
}

output "job_id" {
  value = databricks_job.dlt_pipeline.id
}
