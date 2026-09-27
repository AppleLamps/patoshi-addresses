-- Column names were inspected from the live BigQuery table metadata first.
-- Value units are deliberately left raw until the 52.01 BTC control establishes them.
SELECT
  t.block_number AS height,
  t.block_hash,
  CAST(t.block_timestamp AS STRING) AS block_timestamp,
  t.hash AS coinbase_txid,
  t.version AS tx_version,
  t.lock_time,
  t.input_count,
  t.output_count,
  t.inputs[SAFE_OFFSET(0)].script_hex AS input_script,
  t.inputs[SAFE_OFFSET(0)].sequence AS input_sequence,
  o.index AS output_index,
  o.script_hex AS output_script,
  o.type AS output_type,
  CAST(o.value AS STRING) AS output_value_raw,
  TO_JSON_STRING(t.outputs) AS all_outputs_json,
  b.nonce,
  b.bits,
  b.version AS block_version,
  b.merkle_root,
  b.transaction_count,
  b.coinbase_param
FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
CROSS JOIN UNNEST(t.outputs) AS o
JOIN `bigquery-public-data.crypto_bitcoin.blocks` AS b
  ON b.hash = t.block_hash AND b.number = t.block_number
WHERE t.is_coinbase
  AND o.index = 0
  AND t.block_number IN UNNEST(@heights)
  AND t.block_timestamp >= TIMESTAMP('2009-01-01')
  AND t.block_timestamp < TIMESTAMP('2011-01-01')
ORDER BY height;
