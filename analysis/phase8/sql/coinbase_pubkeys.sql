-- Output 0 of every coinbase at heights 0 to 54,619 (all are single-output P2PK in this range).
-- The public key is read from the locking script offline and checked against the Phase 5 address.
SELECT
  t.block_number AS height,
  t.hash AS coinbase_txid,
  o.index AS output_index,
  o.type AS output_type,
  o.script_hex AS output_script,
  CAST(o.value AS STRING) AS value_raw
FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
CROSS JOIN UNNEST(t.outputs) AS o
WHERE t.is_coinbase
  AND t.block_number BETWEEN 0 AND 54619
  AND t.block_timestamp_month < DATE('2010-06-01')
ORDER BY height, output_index;
