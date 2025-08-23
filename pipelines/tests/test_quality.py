def test_not_null_customer_id(spark):
    df = spark.table("uc.analytics.customer_profile")
    assert df.filter("customer_id IS NULL").count() == 0
