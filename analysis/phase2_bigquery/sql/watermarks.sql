-- Establish table-specific coverage; a block-table watermark alone does not
-- establish that the input index is equally current.
SELECT 'inputs' AS source_table, MAX(block_number) AS maximum_block_height,
  CAST(MAX(block_timestamp) AS STRING) AS maximum_block_timestamp,
  CAST(CURRENT_TIMESTAMP() AS STRING) AS observed_at
FROM `bigquery-public-data.crypto_bitcoin.inputs`
UNION ALL
SELECT 'transactions', MAX(block_number), CAST(MAX(block_timestamp) AS STRING),
  CAST(CURRENT_TIMESTAMP() AS STRING)
FROM `bigquery-public-data.crypto_bitcoin.transactions`;
