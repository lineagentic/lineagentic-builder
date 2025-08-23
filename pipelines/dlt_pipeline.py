# Minimal Spark job; replace with DLT or production code
from pyspark.sql import functions as F

df = spark.table("raw.crm_customers")
clean = (
    df.filter(F.col("customer_id").isNotNull())
      .withColumn("email", F.lower(F.col("email")))
)

clean.write.mode("overwrite").saveAsTable("uc.analytics.customer_profile")
