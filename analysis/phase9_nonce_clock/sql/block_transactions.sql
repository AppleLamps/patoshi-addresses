-- Every transaction in blocks at heights <= 54,619 with three or more transactions (from the committed headers),
-- with the previous txids its inputs spend. In-block order is not in the table; it is tested against the Merkle root offline.
SELECT
  t.block_number AS height,
  t.hash AS txid,
  t.is_coinbase,
  ARRAY_TO_STRING(ARRAY(SELECT i.spent_transaction_hash FROM UNNEST(t.inputs) AS i WHERE i.spent_transaction_hash IS NOT NULL), ';') AS prev_txids
FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
WHERE t.block_number IN UNNEST(@heights)
  AND t.block_timestamp_month < DATE('2010-06-01')
ORDER BY height, txid;
