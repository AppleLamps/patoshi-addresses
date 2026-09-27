SELECT CURRENT_TIMESTAMP() AS query_snapshot_at,
  MAX(number) AS maximum_block_height,
  MAX(timestamp) AS maximum_block_timestamp,
  COUNT(*) AS blocks_available
FROM `bigquery-public-data.crypto_bitcoin.blocks`;
