-- Phase 5 co-spend census: every output of every coinbase at heights 0 to 54,619, plus every input of every
-- transaction (to the frozen watermark, block 968,902) that spends at least one of those outputs.
-- One pass over the inputs view: the window keeps whole transactions, so co-spent inputs come back without a
-- second scan. Rows are tagged coinbase_output or spending_input and share one column set.
WITH cb AS (
  SELECT
    t.block_number AS coinbase_height,
    t.hash AS coinbase_txid,
    CAST(t.block_timestamp AS STRING) AS coinbase_time,
    o.index AS vout,
    CAST(o.value AS STRING) AS value_sats,
    o.type AS output_type,
    ARRAY_TO_STRING(o.addresses, ' ') AS address
  FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
  CROSS JOIN UNNEST(t.outputs) AS o
  WHERE t.is_coinbase
    AND t.block_number BETWEEN 0 AND 54619
    AND t.block_timestamp_month < DATE '2010-06-01'
),
spending_inputs AS (
  SELECT
    i.transaction_hash AS spending_txid,
    i.block_number AS spending_height,
    CAST(i.block_timestamp AS STRING) AS spending_time,
    i.index AS vin,
    i.spent_transaction_hash AS prev_txid,
    i.spent_output_index AS prev_vout,
    cb.coinbase_height
  FROM `bigquery-public-data.crypto_bitcoin.inputs` AS i
  LEFT JOIN cb
    ON i.spent_transaction_hash = cb.coinbase_txid AND i.spent_output_index = cb.vout
  WHERE i.block_number <= 968902
  QUALIFY LOGICAL_OR(cb.coinbase_txid IS NOT NULL) OVER (PARTITION BY i.transaction_hash)
)
SELECT
  'coinbase_output' AS row_kind, coinbase_height AS height, coinbase_txid AS txid, vout AS idx,
  coinbase_time AS time, CAST(NULL AS STRING) AS prev_txid, CAST(NULL AS INT64) AS prev_vout,
  value_sats, output_type, address, CAST(NULL AS INT64) AS coinbase_height
FROM cb
UNION ALL
SELECT
  'spending_input', spending_height, spending_txid, vin, spending_time, prev_txid, prev_vout,
  CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), coinbase_height
FROM spending_inputs
ORDER BY row_kind, height, txid, idx;
