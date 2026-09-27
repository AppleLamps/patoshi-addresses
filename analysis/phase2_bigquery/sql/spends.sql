-- ALL inputs, with no date restriction: the spend could occur at any later height.
-- Outpoints come from the cached, verified-height coinbase query result.
WITH target AS (SELECT height, txid FROM UNNEST(@outpoints))
SELECT
  t.height AS coinbase_height,
  t.txid AS coinbase_txid,
  0 AS coinbase_output_index,
  i.transaction_hash AS spending_txid,
  i.index AS spending_input_index,
  i.block_number AS spending_height,
  CAST(i.block_timestamp AS STRING) AS spending_timestamp,
  i.spent_transaction_hash,
  i.spent_output_index
FROM `bigquery-public-data.crypto_bitcoin.inputs` AS i
JOIN target AS t ON i.spent_transaction_hash = t.txid
WHERE i.spent_output_index = 0
ORDER BY coinbase_height, spending_height;
